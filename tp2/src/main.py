"""Punto de entrada: la app FastAPI y el arranque del servidor."""
import asyncio
import signal
import time
from contextlib import asynccontextmanager
from typing import get_args

import uvicorn
from fastapi import FastAPI, HTTPException, Query

import estado
import persistencia
import workers
from modelos import Estado, TareaNueva

LIMITE_APAGADO = 8   # Docker manda SIGKILL a los 10 s del SIGTERM: margen para volcar

log = persistencia.log
_handlers_uvicorn: dict[signal.Signals, object] = {}   # los que pisamos, para devolverles la posta
_apagado: asyncio.Task | None = None


def al_recibir_senal(sig: signal.Signals):
    """Handler de SIGTERM/SIGINT. Corre en el loop (add_signal_handler), no en el
    medio de cualquier línea como un handler de signal.signal: puede crear tasks.
    Solo dispara el apagado; el trabajo lo hace la corrutina apagar()."""
    global _apagado
    if estado.apagando:
        log.info(f'{sig.name} otra vez: el apagado ya está en curso')
        return
    estado.apagando = True        # desde acá el POST responde 503
    log.info(f'{sig.name} recibida: apagado ordenado (límite {LIMITE_APAGADO} s)')
    _apagado = asyncio.create_task(apagar(sig))


async def apagar(sig: signal.Signals):
    t0 = time.perf_counter()
    await workers.detener(LIMITE_APAGADO)
    ruta = persistencia.volcar(estado.tareas)
    log.info(f'estado volcado en {ruta} ({time.perf_counter() - t0:.2f} s)')
    # Recién ahora le pasamos la señal al handler de uvicorn que habíamos pisado:
    # es el que le dice a uvicorn que deje de escuchar y salga. Así anda igual con
    # `python main.py` (Docker) que con `uvicorn main:app [--reload]`.
    handler = _handlers_uvicorn.get(sig)
    if callable(handler):
        handler(sig, None)


@asynccontextmanager
async def ciclo(app):
    # Antes del yield: al arrancar, con el loop corriendo
    persistencia.reportar_volcado_previo()
    workers.iniciar()
    loop = asyncio.get_running_loop()
    # uvicorn ya instaló sus handlers (signal.signal) antes del lifespan: un
    # proceso tiene UN handler por señal, así que los nuestros los reemplazan.
    # Guardamos los de uvicorn para llamarlos cuando termine nuestro apagado.
    for sig in (signal.SIGTERM, signal.SIGINT):
        _handlers_uvicorn[sig] = signal.getsignal(sig)
        loop.add_signal_handler(sig, al_recibir_senal, sig)
    yield
    # Después del yield: uvicorn se está yendo. Si fue por nuestra señal, el
    # apagado ya corrió (o está terminando); si no (ej. --reload), lo hacemos acá.
    if _apagado is not None:
        await _apagado
    else:
        estado.apagando = True
        await workers.detener(LIMITE_APAGADO)
        persistencia.volcar(estado.tareas)


app = FastAPI(title='Plataforma de tareas', lifespan=ciclo)


@app.get('/')
async def raiz():
    return {'servicio': 'tareas', 'docs': '/docs'}


@app.post('/tareas', status_code=202)
async def crear_tarea(nueva: TareaNueva):
    """Registra la tarea y responde YA: 202 = recibida, se procesa después."""
    if estado.apagando:
        # 503 = "ahora no puedo atenderte" (error del servidor, temporal)
        raise HTTPException(status_code=503, detail='El servidor se está apagando',
                            headers={'Retry-After': '30'})
    # Backpressure. Se chequea ANTES de crear la tarea (si no, quedaría 'pendiente'
    # en el dict sin estar en la cola). Entre este full() y el put_nowait() no hay
    # ningún await: nadie puede llenar la cola en el medio.
    if workers.cola.full():
        raise HTTPException(status_code=503,
                            detail=f'Cola llena ({workers.MAX_COLA} tareas esperando)',
                            headers={'Retry-After': '5'})
    tid = estado.nuevo_id()
    tarea = {
        'id': tid,
        'tipo': nueva.tipo,
        # mode='json': las HttpUrl pasan a str, así el dict se puede volcar a JSON
        'parametros': nueva.parametros.model_dump(mode='json'),
        'timeout': nueva.timeout,
        'estado': 'pendiente',
        'resultado': None,
        'error': None,
        'creada': time.time(),
        'iniciada': None,
        'finalizada': None,
    }
    estado.tareas[tid] = tarea
    # put_nowait y no `await put`: con la cola llena, `await put` dejaría al cliente
    # colgado esperando lugar (y el POST tiene que responder ya)
    workers.cola.put_nowait(tid)
    return tarea


@app.get('/tareas')
async def listar_tareas(estado_filtro: Estado | None = Query(default=None, alias='estado')):
    """Todas las tareas, o solo las de un estado: GET /tareas?estado=pendiente"""
    todas = estado.tareas.values()
    if estado_filtro is None:
        return list(todas)
    return [t for t in todas if t['estado'] == estado_filtro]


@app.get('/tareas/{tid}')
async def obtener_tarea(tid: int):
    if tid not in estado.tareas:
        raise HTTPException(status_code=404, detail=f'No existe la tarea {tid}')
    return estado.tareas[tid]


def _promedio(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 3) if valores else None


def _tiempos(tareas: list[dict]) -> dict:
    """Promedios de un grupo de tareas. Cada tiempo usa SOLO las que lo tienen válido:
    - espera en cola: toda tarea que arrancó (también fallidas y canceladas en
      ejecución: esperaron igual). Las que nunca arrancaron no tienen el dato.
    - ejecución: solo las completadas. Una fallida por timeout tiene los números,
      pero su "ejecución" es el timeout: dice cuándo la cortamos, no cuánto cuesta.
    """
    arrancadas = [t for t in tareas if t['iniciada'] is not None]
    completadas = [t for t in tareas if t['estado'] == 'completada']
    return {
        'espera_en_cola': _promedio([t['iniciada'] - t['creada'] for t in arrancadas]),
        'ejecucion': _promedio([t['finalizada'] - t['iniciada'] for t in completadas]),
        'completadas': len(completadas),
    }


@app.get('/estadisticas')
async def estadisticas():
    todas = list(estado.tareas.values())
    por_estado = {e: 0 for e in get_args(Estado)}
    for t in todas:
        por_estado[t['estado']] += 1
    tipos = sorted({t['tipo'] for t in todas})
    return {
        'total': len(todas),
        'por_estado': por_estado,
        'workers': {
            'total': workers.N_WORKERS,
            # cada worker ocupado tiene exactamente una ejecución en curso
            'ocupados': len(estado.en_ejecucion),
        },
        'tiempos_promedio_s': {
            'general': _tiempos(todas),
            'por_tipo': {tipo: _tiempos([t for t in todas if t['tipo'] == tipo])
                         for tipo in tipos},
        },
    }


@app.delete('/tareas/{tid}')
async def cancelar_tarea(tid: int):
    """Cancela una tarea pendiente (flecha 1) o en ejecución (flecha 3)."""
    if tid not in estado.tareas:
        raise HTTPException(status_code=404, detail=f'No existe la tarea {tid}')
    tarea = estado.tareas[tid]

    if tarea['estado'] == 'pendiente':
        # Sigue en la cola (no se puede sacar del medio): el worker la va a saltear
        tarea['estado'] = 'cancelada'
        tarea['finalizada'] = time.time()
        return tarea

    t = estado.en_ejecucion.get(tid)
    # cancel() devuelve False si el Task justo terminó: ya no hay nada que cortar
    if tarea['estado'] == 'ejecutando' and t is not None and t.cancel():
        tarea['estado'] = 'cancelada'   # el worker también lo va a marcar al enterarse
        return tarea

    raise HTTPException(
        status_code=409,
        detail=f"La tarea {tid} ya está {tarea['estado']}: no se puede cancelar",
    )


# La guarda importa: con spawn (macOS/Windows) los procesos del
# ProcessPoolExecutor re-importan este módulo y sin ella arrancarían
# otro servidor cada uno.
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

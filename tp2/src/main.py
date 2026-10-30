"""Punto de entrada: la app FastAPI y el arranque del servidor."""
import asyncio
import signal
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query

import estado
import persistencia
import workers
from modelos import Estado, TareaNueva

LIMITE_APAGADO = 8   # Docker manda SIGKILL a los 10 s del SIGTERM: margen para volcar

log = persistencia.log
servidor: uvicorn.Server | None = None   # lo crea el __main__; el handler le pide salir
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
    _apagado = asyncio.create_task(apagar())


async def apagar():
    t0 = time.perf_counter()
    await workers.detener(LIMITE_APAGADO)
    ruta = persistencia.volcar(estado.tareas)
    log.info(f'estado volcado en {ruta} ({time.perf_counter() - t0:.2f} s)')
    if servidor is not None:
        servidor.should_exit = True   # recién ahora uvicorn deja de escuchar y sale


@asynccontextmanager
async def ciclo(app):
    # Antes del yield: al arrancar, con el loop corriendo
    persistencia.reportar_volcado_previo()
    workers.iniciar()
    loop = asyncio.get_running_loop()
    # uvicorn ya instaló sus handlers (signal.signal) antes del lifespan:
    # estos los reemplazan.
    for sig in (signal.SIGTERM, signal.SIGINT):
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
    workers.cola.put_nowait(tid)   # sin await: la cola no tiene límite, nunca espera
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
    # Server en vez de uvicorn.run(): necesitamos la referencia para should_exit
    servidor = uvicorn.Server(uvicorn.Config(app, host='0.0.0.0', port=8000))
    servidor.run()

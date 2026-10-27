"""Punto de entrada: la app FastAPI y el arranque del servidor."""
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query

import estado
import workers
from modelos import Estado, TareaNueva


@asynccontextmanager
async def ciclo(app):
    workers.iniciar()        # antes del yield: al arrancar, con el loop corriendo
    yield
    await workers.detener()  # después del yield: al apagar


app = FastAPI(title='Plataforma de tareas', lifespan=ciclo)


@app.get('/')
async def raiz():
    return {'servicio': 'tareas', 'docs': '/docs'}


@app.post('/tareas', status_code=202)
async def crear_tarea(nueva: TareaNueva):
    """Registra la tarea y responde YA: 202 = recibida, se procesa después."""
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
    uvicorn.run(app, host='0.0.0.0', port=8000)

#!/usr/bin/env python3
"""Esqueleto del TP2: API + cola + workers + executor.

Ejercicio 5 de la clase 21, partiendo de api.py de la clase 19.

Uso:
    python3 api_tp2.py
"""
import asyncio
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal, get_args

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

N_WORKERS = 4
MAXSIZE = 10              # backpressure: más que esto esperando -> 503
VUELTAS = 2_000_000       # ~1.5 s de CPU en tu máquina
SEGUNDOS_ESPERAR = 3
SEGUNDOS_DESCARGAR = 1
TIMEOUT_APAGADO = 10   # si los workers no terminan en esto, se cancelan

Estado = Literal['pendiente', 'ejecutando', 'completada', 'error', 'cancelada']

tareas: dict[int, dict] = {}
en_ejecucion: dict[int, asyncio.Task] = {}   # id -> task, para poder cancelarla
CENTINELA = object()                         # 'no hay más trabajo'
proximo_id = 0


# ---------------------------------------------------------------
# El trabajo
# ---------------------------------------------------------------

def hashear(vueltas):
    """CPU-bound. A nivel de módulo para que el pool la pueda picklear."""
    h = b'x'
    for _ in range(vueltas):
        h = hashlib.sha256(h).digest()
    return h.hex()[:8]


async def ejecutar(tarea, pool):
    """Decide DÓNDE corre cada tipo de tarea."""
    if tarea['tipo'] == 'hashear':
        loop = asyncio.get_running_loop()
        h = await loop.run_in_executor(pool, hashear, VUELTAS)   # CPU -> otro proceso
        return f'hash {h}'
    if tarea['tipo'] == 'esperar':
        await asyncio.sleep(SEGUNDOS_ESPERAR)                     # espera -> en el loop
        return f'esperé {SEGUNDOS_ESPERAR}s'
    # 'descargar': I/O simulado, también en el loop
    await asyncio.sleep(SEGUNDOS_DESCARGAR)
    return 'descarga simulada ok'


async def worker(wid, cola, pool):
    """Saca un id, lanza la tarea como task propia (para poder cancelarla sola)."""
    while True:
        tid = await cola.get()
        if tid is CENTINELA:
            cola.task_done()
            print(f'  worker {wid}: me retiro')
            return
        try:
            tarea = tareas.get(tid)
            if tarea is None or tarea['estado'] == 'cancelada':
                continue                   # borrada o cancelada mientras esperaba
            tarea['estado'] = 'ejecutando'
            t = asyncio.create_task(ejecutar(tarea, pool))
            en_ejecucion[tid] = t
            try:
                tarea['resultado'] = await t
                tarea['estado'] = 'completada'
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    raise                  # cancelaron al WORKER (apagado): no tragarla
                tarea['estado'] = 'cancelada'   # cancelaron solo la TAREA (DELETE)
            finally:
                en_ejecucion.pop(tid, None)
        except Exception as e:
            # Lo mínimo: que un error en UNA tarea no mate al worker
            tarea['estado'] = 'error'
            tarea['resultado'] = f'{type(e).__name__}: {e}'
        finally:
            cola.task_done()

# ---------------------------------------------------------------
# Arranque y apagado
# ---------------------------------------------------------------

@asynccontextmanager
async def ciclo(app):
    app.state.cola = asyncio.Queue(maxsize=MAXSIZE)
    app.state.pool = ProcessPoolExecutor(max_workers=2)
    app.state.workers = [
        asyncio.create_task(worker(i, app.state.cola, app.state.pool))
        for i in range(N_WORKERS)
    ]
    yield
    t0 = time.perf_counter()
    cola, workers = app.state.cola, app.state.workers

    # 1. Lo que no arrancó no se va a hacer: sacarlo de la cola y marcarlo
    descartadas = 0
    while not cola.empty():
        tid = cola.get_nowait()
        cola.task_done()
        if tid in tareas and tareas[tid]['estado'] == 'pendiente':
            tareas[tid]['estado'] = 'cancelada'
            descartadas += 1
    print(f'apagado: {descartadas} pendientes descartadas, '
          f'{len(en_ejecucion)} en ejecución, esperando que terminen...')

    # 2. Un centinela por worker: cada uno termina lo suyo y se retira
    for _ in workers:
        cola.put_nowait(CENTINELA)

    # 3. Esperarlos, pero no para siempre
    try:
        await asyncio.wait_for(asyncio.gather(*workers), timeout=TIMEOUT_APAGADO)
    except TimeoutError:
        print(f'apagado: pasaron {TIMEOUT_APAGADO}s, cancelo lo que quedó')
        await asyncio.gather(*workers, return_exceptions=True)

    app.state.pool.shutdown(cancel_futures=True)
    print(f'apagado: pool cerrado, todo listo en {time.perf_counter() - t0:.2f}s')


app = FastAPI(
    title='Tareas',
    description='Esqueleto del TP2 (clase 21)',
    lifespan=ciclo,
)


# ---------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------

class TareaNueva(BaseModel):
    """Lo que el cliente manda en el cuerpo de un POST."""
    tipo: Literal['descargar', 'hashear', 'esperar']
    prioridad: int = Field(default=1, ge=1, le=5,
                           description='1 = más baja, 5 = más alta')


class Tarea(TareaNueva):
    """Lo que devolvemos."""
    id: int
    estado: Estado = 'pendiente'
    resultado: str | None = None


# ---------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------

@app.get('/')
async def raiz():
    return {'servicio': 'tareas', 'docs': '/docs'}


@app.post('/tareas', response_model=Tarea, status_code=202)
async def crear(nueva: TareaNueva):
    """202 Accepted: la recibí, se va a procesar después."""
    global proximo_id
    tid = proximo_id + 1
    tarea = {'id': tid, **nueva.model_dump(), 'estado': 'pendiente', 'resultado': None}
    try:
        app.state.cola.put_nowait(tid)        # sin await: si está llena, falla YA
    except asyncio.QueueFull:
        raise HTTPException(
            status_code=503,
            detail=f'Cola llena: ya hay {MAXSIZE} tareas esperando',
            headers={'Retry-After': '5'},
        )
    # Entre el put y estas líneas no hay await: ningún worker puede
    # sacar el id antes de que la tarea exista en el diccionario.
    proximo_id = tid
    tareas[tid] = tarea
    return tarea


@app.get('/tareas', response_model=list[Tarea])
async def listar(
    estado: Estado | None = Query(default=None, description='Filtrar por estado'),
    limite: int = Query(default=10, ge=1, le=100),
):
    items = list(tareas.values())
    if estado:
        items = [t for t in items if t['estado'] == estado]
    return items[:limite]


@app.get('/tareas/{tarea_id}', response_model=Tarea)
async def obtener(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    return tareas[tarea_id]


@app.get('/estadisticas')
async def estadisticas():
    conteo = {e: 0 for e in get_args(Estado)}
    for t in tareas.values():
        conteo[t['estado']] += 1
    return {'total': len(tareas), 'por_estado': conteo,
            'en_cola': app.state.cola.qsize()}


@app.delete('/tareas/{tarea_id}', response_model=Tarea)
async def cancelar(tarea_id: int):
    """Cancela una tarea pendiente o en ejecución."""
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    tarea = tareas[tarea_id]
    if tarea['estado'] == 'pendiente':
        tarea['estado'] = 'cancelada'          # el worker la va a saltear
    elif tarea['estado'] == 'ejecutando' and en_ejecucion[tarea_id].cancel():
        tarea['estado'] = 'cancelada'          # cancel() da False si justo terminó
    else:
        raise HTTPException(
            status_code=409,
            detail=f"La tarea ya está {tarea['estado']}: no hay nada que cancelar",
        )
    return tarea


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

#!/usr/bin/env python3
"""Una API con FastAPI: validación, errores y documentación automática.

Es el esqueleto de lo que pide el TP2, con los datos en memoria y sin
concurrencia todavía.

Uso:
    pip install fastapi uvicorn
    python3 api.py

Después:
    http://localhost:8000/docs        <- la documentación se genera sola
    curl localhost:8000/tareas
    curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
         -d '{"tipo":"descargar","prioridad":3}'
"""
import asyncio
import hashlib
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

VUELTAS = 3_000_000          # ~3 s en tu máquina


def hashear():
    """CPU-bound puro. A nivel de módulo, para que el pool la pueda picklear."""
    h = b'x'
    for _ in range(VUELTAS):
        h = hashlib.sha256(h).digest()
    return h.hex()[:8]


@asynccontextmanager
async def ciclo(app):
    app.state.pool = ProcessPoolExecutor(max_workers=2)   # una vez, al arrancar
    yield
    app.state.pool.shutdown()


app = FastAPI(
    title='Tareas',
    description='Ejemplo de la clase 19: HTTP + FastAPI',
    lifespan=ciclo,
)

# Estado en memoria. OJO: con --workers > 1 cada proceso tiene el suyo.
tareas: dict[int, dict] = {}
proximo_id = 0
MAX_PENDIENTES = 10


# ---------------------------------------------------------------
# Modelos: Pydantic valida por nosotros
# ---------------------------------------------------------------

class TareaNueva(BaseModel):
    """Lo que el cliente manda en el cuerpo de un POST."""
    tipo: Literal['descargar', 'hashear', 'esperar']
    prioridad: int = Field(default=1, ge=1, le=5,
                           description='1 = más baja, 5 = más alta')


class Tarea(TareaNueva):
    """Lo que devolvemos: lo anterior más lo que agrega el servidor."""
    id: int
    estado: Literal['pendiente', 'ejecutando', 'completada'] = 'pendiente'


# ---------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------

@app.get('/')
async def raiz():
    """FastAPI convierte el dict a JSON y pone los headers por su cuenta."""
    return {'servicio': 'tareas', 'docs': '/docs'}


@app.get('/tareas', response_model=list[Tarea])
async def listar(
    estado: str | None = Query(default=None, description='Filtrar por estado'),
    limite: int = Query(default=10, ge=1, le=100),
):
    """Los parámetros que no están en la ruta se leen de la query string.
    Los tipos NO son decorativos: FastAPI valida y convierte."""
    items = list(tareas.values())
    if estado:
        items = [t for t in items if t['estado'] == estado]
    return items[:limite]


@app.post('/tareas', response_model=Tarea, status_code=201)
async def crear(nueva: TareaNueva):
    """201 Created es la respuesta correcta a un POST que crea algo."""
    global proximo_id
    pendientes = sum(1 for t in tareas.values() if t['estado'] == 'pendiente')
    if pendientes >= MAX_PENDIENTES:
        raise HTTPException(
            status_code=503,
            detail=f'Cola llena: ya hay {MAX_PENDIENTES} tareas pendientes',
            headers={'Retry-After': '5'},
        )
    proximo_id += 1
    tarea = {'id': proximo_id, **nueva.model_dump(), 'estado': 'pendiente'}
    tareas[proximo_id] = tarea
    return tarea


@app.get('/tareas/{tarea_id}', response_model=Tarea)
async def obtener(tarea_id: int):
    """El : int hace que /tareas/abc devuelva 422 sin ejecutar la función."""
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    return tareas[tarea_id]


@app.delete('/tareas/{tarea_id}', status_code=204)
async def borrar(tarea_id: int):
    """204 No Content: salió bien y no hay nada que devolver."""
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    del tareas[tarea_id]


@app.get('/quien-soy')
async def quien_soy():
    """Dónde corre realmente un endpoint async."""
    loop = asyncio.get_running_loop()
    return {
        'pid': os.getpid(),
        'thread': threading.current_thread().name,
        'loop': type(loop).__name__,
        'id_del_loop': id(loop),        # igual en todos los pedidos
    }


@app.get('/quien-soy-sync')
def quien_soy_sync():
    """Un def común NO corre en el event loop: va a un threadpool."""
    try:
        asyncio.get_running_loop()
        estado = 'HAY loop'
    except RuntimeError:
        estado = 'NO hay loop corriendo acá'
    return {'thread': threading.current_thread().name, 'loop': estado}


# ---------------------------------------------------------------
# Ejercicio 3, parte C
# ---------------------------------------------------------------

class TareaCambios(BaseModel):
    """Para PATCH: todo opcional, se aplica solo lo que el cliente mande."""
    tipo: Literal['descargar', 'hashear', 'esperar'] | None = None
    prioridad: int | None = Field(default=None, ge=1, le=5)
    estado: Literal['pendiente', 'ejecutando', 'completada'] | None = None


@app.patch('/tareas/{tarea_id}', response_model=Tarea)
async def modificar(tarea_id: int, cambios: TareaCambios):
    """exclude_unset: solo los campos que vinieron en el JSON, no los None por defecto."""
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    tareas[tarea_id].update(cambios.model_dump(exclude_unset=True))
    return tareas[tarea_id]


@app.get('/estadisticas')
async def estadisticas():
    """Cantidad de tareas por estado, incluyendo los que tienen cero."""
    conteo = {'pendiente': 0, 'ejecutando': 0, 'completada': 0}
    for t in tareas.values():
        conteo[t['estado']] += 1
    return {'total': len(tareas), 'por_estado': conteo}


# ---------------------------------------------------------------
# Clase 21, ejercicio 3, parte D
# ---------------------------------------------------------------

@app.post('/hashear')
async def hashear_bloqueante():
    """Sin executor: el cálculo corre EN el loop y lo congela."""
    t0 = time.perf_counter()
    h = hashear()
    return {'hash': h, 'segundos': round(time.perf_counter() - t0, 2),
            'modo': 'sin executor'}


@app.post('/hashear-pool')
async def hashear_con_pool():
    """Con executor: el cálculo va a otro proceso y el loop queda libre."""
    t0 = time.perf_counter()
    loop = asyncio.get_running_loop()
    h = await loop.run_in_executor(app.state.pool, hashear)
    return {'hash': h, 'segundos': round(time.perf_counter() - t0, 2),
            'modo': 'ProcessPoolExecutor'}


if __name__ == '__main__':
    import uvicorn
    # uvicorn es el que crea y corre el event loop; FastAPI solo responde.
    uvicorn.run(app, host='127.0.0.1', port=8000)

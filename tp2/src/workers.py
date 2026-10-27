"""La cola de tareas (asyncio.Queue) y el pool de workers que la consumen."""
import asyncio
import os
import time
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor

import estado
import tareas

N_WORKERS = int(os.environ.get('N_WORKERS', 4))

# Dónde corre hashear (CPU-bound). Configurable para poder MEDIR las tres:
#   'proceso'    -> ProcessPoolExecutor: otro proceso, otro GIL (el correcto)
#   'thread'     -> ThreadPoolExecutor: otro hilo, MISMO GIL
#   'bloqueante' -> en el hilo del loop, MAL A PROPÓSITO (medición 2)
MODO_CPU = os.environ.get('MODO_CPU', 'proceso')
_pool: Executor | None = None

# En la cola van solo ids: la única fuente de verdad es estado.tareas.
cola: asyncio.Queue[int] = asyncio.Queue()
_workers: list[asyncio.Task] = []


async def ejecutar(tarea: dict) -> str:
    """Hace el trabajo según el tipo. PROVISORIO: descargar es falso."""
    p = tarea['parametros']
    if tarea['tipo'] == 'esperar':
        return await tareas.esperar(p['segundos'])
    if tarea['tipo'] == 'hashear':
        if MODO_CPU == 'bloqueante':
            return tareas.hashear(p['texto'], p['iteraciones'])   # congela el loop
        loop = asyncio.get_running_loop()
        # Manda la función al pool y devuelve un future: el await suspende
        # SOLO a esta corrutina mientras el pool calcula; el loop sigue.
        return await loop.run_in_executor(
            _pool, tareas.hashear, p['texto'], p['iteraciones'])
    await asyncio.sleep(1)   # simulación hasta que exista en tareas.py
    return f"{tarea['tipo']} simulado"


async def worker(n: int):
    """Saca ids de la cola, uno por vez, para siempre."""
    while True:
        tid = await cola.get()       # se suspende si la cola está vacía: el loop sigue
        tarea = estado.tareas[tid]
        try:
            if tarea['estado'] == 'cancelada':
                continue             # la cancelaron mientras esperaba en la cola
            tarea['estado'] = 'ejecutando'
            tarea['iniciada'] = time.time()
            # Task propio: el DELETE cancela ESTA ejecución, no al worker
            t = asyncio.create_task(ejecutar(tarea))
            estado.en_ejecucion[tid] = t
            try:
                async with asyncio.timeout(tarea['timeout']):
                    tarea['resultado'] = await t
                tarea['estado'] = 'completada'
            except asyncio.CancelledError:
                if asyncio.current_task().cancelling():
                    raise            # cancelaron al WORKER (apagado): que muera
                tarea['estado'] = 'cancelada'   # cancelaron solo la TAREA (DELETE)
            except TimeoutError:
                tarea['estado'] = 'fallida'
                tarea['error'] = f"timeout: superó {tarea['timeout']} s"
            except Exception as e:
                # Una tarea que falla no puede matar al worker
                tarea['estado'] = 'fallida'
                tarea['error'] = f'{type(e).__name__}: {e}'
            finally:
                estado.en_ejecucion.pop(tid, None)   # ya no se está ejecutando
            tarea['finalizada'] = time.time()
        finally:
            cola.task_done()         # pase lo que pase (incluso con el continue)


def iniciar():
    """Lanza los N workers. Se llama al arrancar, con el event loop ya corriendo."""
    global _pool
    if MODO_CPU == 'proceso':
        _pool = ProcessPoolExecutor()    # un proceso por núcleo (os.cpu_count())
    elif MODO_CPU == 'thread':
        _pool = ThreadPoolExecutor()
    for n in range(N_WORKERS):
        _workers.append(asyncio.create_task(worker(n)))


async def detener():
    """PROVISORIO: los cancela de golpe. El apagado ordenado viene después."""
    for w in _workers:
        w.cancel()
    await asyncio.gather(*_workers, return_exceptions=True)
    if _pool is not None:
        # wait=False: no bloquear el loop esperando. PENDIENTE (apagado ordenado):
        # un hash ya arrancado en otro proceso NO se corta con cancel().
        _pool.shutdown(wait=False, cancel_futures=True)

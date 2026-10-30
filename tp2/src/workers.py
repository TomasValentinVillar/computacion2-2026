"""La cola de tareas (asyncio.Queue) y el pool de workers que la consumen."""
import asyncio
import os
import signal
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


async def ejecutar(tarea: dict) -> str | list[dict]:
    """Hace el trabajo según el tipo y devuelve el resultado."""
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
    # descargar
    resultados = await tareas.descargar(p['urls'])
    if all('error' in r for r in resultados):
        # Ninguna respondió: la tarea no logró nada → except Exception → 'fallida'
        raise RuntimeError(f"fallaron las {len(resultados)} URLs; "
                           f"primera: {resultados[0]['error']}")
    return resultados


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


def _preparar_proceso_del_pool():
    """Corre en cada proceso hijo del pool al arrancar.

    Con fork, el hijo HEREDA los handlers del padre, incluido el de
    add_signal_handler, que solo despierta al loop del padre: en el hijo,
    SIGTERM quedaría en la nada y terminate() no lo mataría (lo medimos: 2.5 s
    de más al salir, esperando un hash que seguía corriendo).
    - SIGINT -> ignorar: Ctrl+C le llega a todo el grupo; decide el padre.
    - SIGTERM -> por defecto (morir): así el padre puede terminarlos.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)


def iniciar():
    """Lanza los N workers. Se llama al arrancar, con el event loop ya corriendo."""
    global _pool
    if MODO_CPU == 'proceso':
        # un proceso por núcleo (os.cpu_count())
        _pool = ProcessPoolExecutor(initializer=_preparar_proceso_del_pool)
    elif MODO_CPU == 'thread':
        _pool = ThreadPoolExecutor()
    for n in range(N_WORKERS):
        _workers.append(asyncio.create_task(worker(n)))


async def detener(limite: float):
    """Apagado ordenado de la ejecución. Pasos (ver notas.md "Apagado ordenado"):

    1. las pendientes -> 'cancelada' (nadie las va a ejecutar; los workers las saltean)
    2. esperar las que se están ejecutando, como máximo `limite` segundos
    3. las que no terminaron -> .cancel() sobre SU Task (no sobre el worker):
       el worker las marca 'cancelada', así ninguna queda 'ejecutando' en el JSON
    4. cancelar los workers (ya ociosos) y cerrar el pool
    """
    ahora = time.time()
    for tarea in estado.tareas.values():
        if tarea['estado'] == 'pendiente':
            tarea['estado'] = 'cancelada'
            tarea['error'] = 'apagado del servidor'
            tarea['finalizada'] = ahora

    corriendo = list(estado.en_ejecucion.values())
    if corriendo:
        _, sin_terminar = await asyncio.wait(corriendo, timeout=limite)
        for t in sin_terminar:
            t.cancel()
        if sin_terminar:
            # Darle al loop una vuelta para que cada worker procese su CancelledError
            await asyncio.wait(sin_terminar, timeout=1)

    for w in _workers:
        w.cancel()
    await asyncio.gather(*_workers, return_exceptions=True)

    if _pool is not None:
        if isinstance(_pool, ProcessPoolExecutor):
            # Un hash ya arrancado en otro proceso NO se corta con cancel(): el
            # proceso sigue calculando y al salir Python lo esperaría (hasta ~20 s,
            # Docker manda SIGKILL a los 10). Se terminan los procesos a mano.
            # _processes es privado; Python 3.14 trae terminate_workers() para esto.
            for p in (_pool._processes or {}).values():
                p.terminate()
        _pool.shutdown(wait=False, cancel_futures=True)

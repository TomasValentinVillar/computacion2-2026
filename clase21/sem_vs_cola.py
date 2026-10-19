import asyncio
import random
import time

random.seed(21)
URLS = [f'https://ejemplo.com/archivo-{i}' for i in range(20)]
DURACION = {u: random.uniform(0.05, 0.25) for u in URLS}   # misma para las dos versiones
LIMITE = 5

activas = 0
max_activas = 0
max_tasks = 0


async def bajar(url):
    """La descarga simulada. Lleva la cuenta de cuántas hay a la vez."""
    global activas, max_activas, max_tasks
    activas += 1
    max_activas = max(max_activas, activas)
    max_tasks = max(max_tasks, len(asyncio.all_tasks()) - 1)   # -1: sin contar main
    await asyncio.sleep(DURACION[url])
    activas -= 1
    return f'{url}: ok'


# --- Versión 1: Semaphore ---
sem = asyncio.Semaphore(LIMITE)

async def bajar_con_sem(url):
    async with sem:
        return await bajar(url)

async def con_semaforo():
    return await asyncio.gather(*(bajar_con_sem(u) for u in URLS))


# --- Versión 2: Queue con 5 workers ---
CENTINELA = object()

async def worker(cola, resultados):
    while True:
        url = await cola.get()
        if url is CENTINELA:
            cola.task_done()
            return
        try:
            resultados[url] = await bajar(url)
        finally:
            cola.task_done()

async def con_cola():
    cola = asyncio.Queue()
    resultados = {}
    workers = [asyncio.create_task(worker(cola, resultados)) for _ in range(LIMITE)]
    for u in URLS:
        await cola.put(u)
    for _ in workers:
        await cola.put(CENTINELA)
    await asyncio.gather(*workers)
    return [resultados[u] for u in URLS]       # mismo orden que las URLs


async def medir(nombre, version):
    global activas, max_activas, max_tasks
    activas = max_activas = max_tasks = 0
    t0 = time.perf_counter()
    res = await version()
    dur = time.perf_counter() - t0
    print(f'  {nombre:<10} {len(res)} descargas en {dur:.2f}s | '
          f'máx. simultáneas: {max_activas} | máx. tasks vivas: {max_tasks}')


async def main():
    print(f'{len(URLS)} descargas, concurrencia máxima {LIMITE}:\n')
    await medir('Semaphore', con_semaforo)
    await medir('Queue', con_cola)
    print(f'\n  Secuencial habría sido: {sum(DURACION.values()):.2f}s')


asyncio.run(main())
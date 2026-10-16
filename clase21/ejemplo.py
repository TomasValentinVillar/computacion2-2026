import asyncio
import random

async def procesar(tarea):
    await asyncio.sleep(random.uniform(0.1, 0.5))  # simula trabajo
    print(f'procesada {tarea}')

async def productor(cola, n):
    for i in range(n):
        await cola.put(f'tarea-{i}')

async def worker(cola, wid):
    while True:
        tarea = await cola.get()
        try:
            await procesar(tarea)
        except Exception as e:
            print(f'worker {wid} falló con {tarea}: {e}')  # el worker sigue vivo
        finally:
            cola.task_done()

async def main():
    cola = asyncio.Queue(maxsize=5)
    workers = [asyncio.create_task(worker(cola, i)) for i in range(3)]

    await productor(cola, 12)
    await cola.join()

    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)  # esperar que terminen de cancelarse

asyncio.run(main())
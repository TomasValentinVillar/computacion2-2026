import asyncio
import random

CENTINELA = object()

async def procesar(item):
    await asyncio.sleep(0.5)
    print(f'procesado {item}')

async def worker(cola, wid):
    while True:
        item = await cola.get()
        if item is CENTINELA:
            cola.task_done()
            print(f'[worker {wid}] recibí centinela, me voy')
            break                                  # salida ordenada
        try:
            await procesar(item)
        except Exception as e:
            print(f'[worker {wid}] error con {item}: {e}')
        finally:
            cola.task_done()

async def main():
    cola = asyncio.Queue(maxsize=5)
    workers = [asyncio.create_task(worker(cola, i)) for i in range(3)]

    for i in range(12):                            # el "productor"
        await cola.put(f'tarea-{i}')

    for _ in range(len(workers)):                  # un centinela por worker
        await cola.put(CENTINELA)

    await asyncio.gather(*workers)                 # esperar que terminen solos
    print('todos los workers terminaron')

asyncio.run(main())
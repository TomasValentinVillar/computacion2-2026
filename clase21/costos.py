import asyncio
import time
from concurrent.futures import ProcessPoolExecutor


def doble(x):
    return x * 2


def largo(datos):
    return len(datos)


async def pregunta_9():
    print('=== 9: mandar una lambda ===')
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=1) as pool:
        try:
            await loop.run_in_executor(pool, lambda x: x * 2, 3)
            print('  funcionó')
        except Exception as e:
            print(f'  {type(e).__name__}: {e}')


async def pregunta_10():
    print('\n=== 10: argumento chico contra argumento grande ===')
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=1) as pool:
        await loop.run_in_executor(pool, doble, 1)       # calentar: que el proceso ya exista

        t0 = time.perf_counter()
        await loop.run_in_executor(pool, largo, [5])
        chico = time.perf_counter() - t0

        datos = list(range(1_000_000))
        t0 = time.perf_counter()
        await loop.run_in_executor(pool, largo, datos)
        grande = time.perf_counter() - t0

        t0 = time.perf_counter()
        largo(datos)
        local = time.perf_counter() - t0

    print(f'  lista de un elemento:     {chico * 1000:8.2f} ms')
    print(f'  lista de un millón:       {grande * 1000:8.2f} ms')
    print(f'  len() local, sin proceso: {local * 1000:8.4f} ms')
    print(f'  el grande cuesta {grande / chico:.0f}x más que el chico')


async def pregunta_11():
    print('\n=== 11: un pool para todo contra un pool por tarea ===')
    N = 20
    loop = asyncio.get_running_loop()

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=2) as pool:
        for i in range(N):
            await loop.run_in_executor(pool, doble, i)
    reusado = time.perf_counter() - t0

    t0 = time.perf_counter()
    for i in range(N):
        with ProcessPoolExecutor(max_workers=2) as pool:
            await loop.run_in_executor(pool, doble, i)
    por_tarea = time.perf_counter() - t0

    print(f'  {N} tareas, un pool reusado:   {reusado:.3f} s')
    print(f'  {N} tareas, un pool por tarea: {por_tarea:.3f} s')
    print(f'  diferencia: {por_tarea / reusado:.0f}x')


async def main():
    await pregunta_9()
    await pregunta_10()
    await pregunta_11()


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""Ejercicio 5.1: asyncio.timeout vs asyncio.wait_for.

Uso:
    python3 timeouts.py
"""
import asyncio
import time

PASO = 0.3
PASOS = 17                        # ~5 segundos en total


async def operacion_lenta(nombre):
    try:
        for i in range(1, PASOS + 1):
            await asyncio.sleep(PASO)
            print(f'    [{nombre}] paso {i:2} ({i * PASO:.1f}s)')
        return 'terminé'
    except asyncio.CancelledError:
        print(f'    [{nombre}] recibí CancelledError')
        raise
    finally:
        print(f'    [{nombre}] finally')


def describir(e, t0):
    dt = time.perf_counter() - t0
    tipo = type(e)
    print(f'  excepción a los {dt:.2f}s: {tipo.__module__}.{tipo.__name__}')


async def con_timeout():
    print('=== asyncio.timeout(2) ===')
    t0 = time.perf_counter()
    try:
        async with asyncio.timeout(2):
            resultado = await operacion_lenta('timeout')
            print(f'  resultado: {resultado}')
    except Exception as e:
        describir(e, t0)
    print('  espero 2s más para ver si la operación sigue...')
    await asyncio.sleep(2)


async def con_wait_for():
    print('\n=== asyncio.wait_for(..., timeout=2) ===')
    t0 = time.perf_counter()
    try:
        resultado = await asyncio.wait_for(operacion_lenta('wait_for'), timeout=2)
        print(f'  resultado: {resultado}')
    except Exception as e:
        describir(e, t0)
    print('  espero 2s más para ver si la operación sigue...')
    await asyncio.sleep(2)


async def main():
    await con_timeout()
    await con_wait_for()
    print(f'\n¿asyncio.TimeoutError es el TimeoutError común? '
          f'{asyncio.TimeoutError is TimeoutError}')


if __name__ == '__main__':
    asyncio.run(main())

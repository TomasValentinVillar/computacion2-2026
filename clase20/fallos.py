#!/usr/bin/env python3
"""Ejercicio 3D: qué pasa con gather cuando una descarga falla.

Uso:
    python3 fallos.py
"""
import asyncio
import time

import httpx

URLS = (['https://example.com'] * 5
        + ['https://esto-no-existe.invalid']
        + ['https://example.com'] * 4)


async def bajar(cliente, i, url):
    r = await cliente.get(url)
    print(f'    #{i} terminó: {r.status_code}')
    return r.status_code


async def gather_normal():
    print('=== gather normal ===')
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=10) as cliente:
        try:
            resultados = await asyncio.gather(
                *(bajar(cliente, i, u) for i, u in enumerate(URLS)))
            print(f'  resultados: {resultados}')
        except Exception as e:
            dt = time.perf_counter() - t0
            print(f'  gather lanzó a los {dt:.2f}s -> {type(e).__name__}: {e}')
            print('  espero 2s para ver qué hacen las demás...')
            await asyncio.sleep(2)


async def gather_con_excepciones():
    print('\n=== gather con return_exceptions=True ===')
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=10) as cliente:
        resultados = await asyncio.gather(
            *(bajar(cliente, i, u) for i, u in enumerate(URLS)),
            return_exceptions=True)
    dt = time.perf_counter() - t0
    print(f'  gather volvió a los {dt:.2f}s con {len(resultados)} resultados:')
    for i, r in enumerate(resultados):
        if isinstance(r, Exception):
            print(f'    #{i}: ERROR {type(r).__name__}: {r}')
        else:
            print(f'    #{i}: {r}')


async def main():
    async with httpx.AsyncClient(timeout=10) as cliente:
        await cliente.get(URLS[0])               # calentamiento (DNS, etc.)
    await gather_normal()
    await gather_con_excepciones()


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""Ejercicio 3C: acotar la concurrencia con un semáforo.

Uso:
    python3 descargas_acotadas.py                  # 10 URLs: sin límite vs Semaphore(3)
    python3 descargas_acotadas.py 200              # 200 URLs, pool de httpx por defecto
    python3 descargas_acotadas.py 200 sinlimite    # 200 URLs, sin ningún tope
"""
import asyncio
import sys
import time

import httpx

URL = 'https://example.com'


async def bajar(cliente, url):
    r = await cliente.get(url)
    return r.status_code


async def sin_limite(cliente, urls):
    return await asyncio.gather(*(bajar(cliente, u) for u in urls))


async def con_semaforo(cliente, urls, n):
    sem = asyncio.Semaphore(n)

    async def acotada(u):
        async with sem:
            return await bajar(cliente, u)

    return await asyncio.gather(*(acotada(u) for u in urls))


async def medir(etiqueta, estrategia, urls, limites, *args):
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10, limits=limites) as cliente:
            codigos = await estrategia(cliente, urls, *args)
        dt = time.perf_counter() - t0
        print(f'  {etiqueta:32} {dt:5.2f}s   códigos: {sorted(set(codigos))}')
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f'  {etiqueta:32} FALLÓ a los {dt:.2f}s')
        print(f'      {type(e).__name__}: {e}')
        if e.__cause__:
            print(f'      causa: {type(e.__cause__).__name__}: {e.__cause__}')


async def main():
    cantidad = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10
    sin_tope = 'sinlimite' in sys.argv
    urls = [URL] * cantidad

    if sin_tope:
        limites = httpx.Limits(max_connections=None, max_keepalive_connections=None)
    else:
        limites = httpx.Limits(max_connections=100, max_keepalive_connections=20)

    async with httpx.AsyncClient(timeout=10) as cliente:
        await cliente.get(URL)                   # calentamiento (DNS, etc.)

    tope = 'sin tope en el pool' if sin_tope else 'pool con tope de 100'
    print(f'{cantidad} descargas de {URL} ({tope})\n')

    await medir('gather, sin semáforo', sin_limite, urls, limites)
    if cantidad <= 10:
        await medir('gather, con Semaphore(3)', con_semaforo, urls, limites, 3)


if __name__ == '__main__':
    asyncio.run(main())

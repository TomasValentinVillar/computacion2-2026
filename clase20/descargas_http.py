#!/usr/bin/env python3
"""Ejercicio 3B: descargas HTTP reales, secuencial vs concurrente."""
import asyncio
import time

import httpx
import requests

URLS = ['https://example.com'] * 10


async def bajar(cliente, url):
    r = await cliente.get(url)
    return url, r.status_code, len(r.content)


async def secuencial_compartido():
    async with httpx.AsyncClient(timeout=10) as cliente:
        return [await bajar(cliente, u) for u in URLS]


async def secuencial_uno_por_descarga():
    resultados = []
    for u in URLS:
        async with httpx.AsyncClient(timeout=10) as cliente:
            resultados.append(await bajar(cliente, u))
    return resultados


async def concurrente():
    async with httpx.AsyncClient(timeout=10) as cliente:
        return await asyncio.gather(*(bajar(cliente, u) for u in URLS))


async def con_requests():
    async def bajar_bloqueante(url):
        r = requests.get(url, timeout=10)        # sin await: bloquea el loop
        return url, r.status_code, len(r.content)
    return await asyncio.gather(*(bajar_bloqueante(u) for u in URLS))


async def main():
    async with httpx.AsyncClient(timeout=10) as cliente:
        await cliente.get(URLS[0])               # calentamiento (DNS, etc.)

    print(f'{len(URLS)} descargas de {URLS[0]}\n')
    for etiqueta, funcion in [
        ('httpx secuencial, 1 cliente',      secuencial_compartido),
        ('httpx secuencial, 1 por descarga', secuencial_uno_por_descarga),
        ('httpx gather',                     concurrente),
        ('requests dentro de gather',        con_requests),
    ]:
        t0 = time.perf_counter()
        resultados = await funcion()
        dt = time.perf_counter() - t0
        codigos = sorted({codigo for _, codigo, _ in resultados})
        print(f'  {etiqueta:34} {dt:5.2f}s   códigos: {codigos}')


if __name__ == '__main__':
    asyncio.run(main())

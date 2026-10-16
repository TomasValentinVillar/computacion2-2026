#!/usr/bin/env python3
"""Formas de escribir un endpoint lento, y cuáles arruinan el servidor.

Primero los tres de la clase (esperas con sleep). Después el mismo
problema con cálculo pesado (un hash iterado), en tres versiones:
en el loop, en el threadpool, y en un pool de procesos.

Mide dos cosas:
  - total: cuánto tardan PEDIDOS pedidos concurrentes
  - ping:  cuánto tarda un pedido trivial mandado MIENTRAS tanto

Uso:
    pip install fastapi uvicorn httpx
    python3 medir.py
"""
import asyncio
import hashlib
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor

from fastapi import FastAPI

PUERTO = 8001
PEDIDOS = 3
DEMORA = 1.0
ITERACIONES = 0          # se calibra en main() para que un hash tarde ~DEMORA

app = FastAPI()
ejecutor = None          # pool de procesos, se crea en levantar()


def hashear(n):
    """Cálculo puro: no espera nada, solo usa CPU (y no suelta el GIL)."""
    h = b'semilla'
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    return h.hex()[:16]


@app.get('/ping')
async def ping():
    """Endpoint trivial: si tarda, es que el loop estaba ocupado."""
    return {'ok': True}


# ---------------------------------------------------------------
# Los tres de la clase: esperas
# ---------------------------------------------------------------

@app.get('/async-bien')
async def async_bien():
    """Corrutina que CEDE el control: el loop atiende a otros mientras."""
    await asyncio.sleep(DEMORA)
    return {'ok': True}


@app.get('/async-mal')
async def async_mal():
    """Corrutina que NO cede: bloquea el event loop y con él a todos."""
    time.sleep(DEMORA)                    # el bug de la clase 18
    return {'ok': True}


@app.get('/sync')
def sincronico():
    """def común: FastAPI lo manda a un threadpool, fuera del loop."""
    time.sleep(DEMORA)
    return {'ok': True}


# ---------------------------------------------------------------
# Ejercicio 5.7: cálculo pesado
# ---------------------------------------------------------------

@app.get('/hash-async')
async def hash_async():
    """El cálculo corre en el loop."""
    return {'hash': hashear(ITERACIONES)}


@app.get('/hash-sync')
def hash_sync():
    """El cálculo corre en un hilo del threadpool."""
    return {'hash': hashear(ITERACIONES)}


@app.get('/hash-proceso')
async def hash_proceso():
    """El cálculo corre en otro proceso; el loop solo espera el resultado."""
    loop = asyncio.get_running_loop()
    resultado = await loop.run_in_executor(ejecutor, hashear, ITERACIONES)
    return {'hash': resultado}


# ---------------------------------------------------------------
# Servidor y mediciones
# ---------------------------------------------------------------

def levantar(iteraciones):
    global ITERACIONES, ejecutor
    ITERACIONES = iteraciones
    # spawn: procesos nuevos y limpios, sin heredar hilos del servidor
    ejecutor = ProcessPoolExecutor(
        max_workers=PEDIDOS,
        mp_context=multiprocessing.get_context('spawn'),
    )
    list(ejecutor.map(hashear, [1] * PEDIDOS))   # calentar: que ya existan
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=PUERTO, log_level='error')


def calibrar():
    """Cuántas iteraciones tardan ~DEMORA segundos en esta máquina."""
    n = 200_000
    t0 = time.perf_counter()
    hashear(n)
    return int(n * DEMORA / (time.perf_counter() - t0))


async def medir(ruta):
    import httpx
    url = f'http://127.0.0.1:{PUERTO}'
    async with httpx.AsyncClient(timeout=60) as cliente:

        async def ping_durante():
            await asyncio.sleep(0.2)          # que los pesados ya estén adentro
            t0 = time.perf_counter()
            await cliente.get(f'{url}/ping')
            return time.perf_counter() - t0

        t0 = time.perf_counter()
        *_, latencia = await asyncio.gather(
            *(cliente.get(f'{url}/{ruta}') for _ in range(PEDIDOS)),
            ping_durante(),
        )
        return time.perf_counter() - t0, latencia


async def correr_mediciones():
    print(f'{PEDIDOS} pedidos concurrentes, cada uno de ~{DEMORA}s, '
          f'y un /ping en el medio:\n')
    print(f'  {"endpoint":<15} {"total":>7} {"ping":>8}')
    print(f'  {"-" * 15} {"-" * 7} {"-" * 8}')
    for ruta in ('async-bien', 'async-mal', 'sync',
                 'hash-async', 'hash-sync', 'hash-proceso'):
        if ruta == 'hash-async':
            print()
        total, latencia = await medir(ruta)
        print(f'  /{ruta:<14} {total:6.2f}s {latencia * 1000:6.0f}ms')


def main():
    global ITERACIONES
    print('Calibrando el hash...', flush=True)
    ITERACIONES = calibrar()
    print(f'  {ITERACIONES:,} iteraciones de sha256 ≈ {DEMORA}s\n', flush=True)

    # No daemon: un proceso daemon no puede tener hijos (el pool los necesita)
    servidor = multiprocessing.Process(target=levantar, args=(ITERACIONES,))
    servidor.start()
    time.sleep(5)                          # levantar uvicorn + calentar el pool
    try:
        asyncio.run(correr_mediciones())
    finally:
        servidor.terminate()
        servidor.join(timeout=5)
        if servidor.is_alive():
            servidor.kill()


if __name__ == '__main__':
    main()

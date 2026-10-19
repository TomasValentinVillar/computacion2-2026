import asyncio
import time

T0 = time.perf_counter()

def ahora():
    return f'[{time.perf_counter() - T0:5.2f}s]'


# --- Pregunta 8: esperar una inicialización ---
async def worker(wid, listo):
    print(f'  {ahora()} worker {wid}: esperando la inicialización')
    await listo.wait()
    print(f'  {ahora()} worker {wid}: arranco a trabajar')

async def inicializar(listo):
    print(f'  {ahora()} init: cargando configuración...')
    await asyncio.sleep(0.5)
    print(f'  {ahora()} init: listo, aviso a todos')
    listo.set()

async def pregunta_8():
    print('=== 8: workers que esperan una inicialización ===')
    listo = asyncio.Event()
    await asyncio.gather(*(worker(i, listo) for i in range(3)), inicializar(listo))


# --- Pregunta 9: set() antes de wait() ---
async def pregunta_9():
    print('\n=== 9: set() antes de que nadie haga wait() ===')
    ev = asyncio.Event()
    ev.set()
    print(f'  is_set() después del set: {ev.is_set()}')
    t = time.perf_counter()
    await ev.wait()
    print(f'  el wait() posterior tardó {(time.perf_counter() - t) * 1000:.3f} ms')
    await ev.wait()
    print(f'  y otro wait() más también pasa: el evento sigue seteado')


# --- Pregunta 10: clear() para pausar y reanudar ---
async def trabajador_pausable(corriendo):
    for i in range(8):
        await corriendo.wait()               # si está pausado, se queda acá
        await asyncio.sleep(0.1)
        print(f'  {ahora()} procesé el item {i}')

async def control(corriendo):
    await asyncio.sleep(0.35)
    corriendo.clear()
    print(f'  {ahora()} control: PAUSA (clear)')
    await asyncio.sleep(0.6)
    corriendo.set()
    print(f'  {ahora()} control: SIGO (set)')

async def pregunta_10():
    print('\n=== 10: clear() para pausar y set() para reanudar ===')
    corriendo = asyncio.Event()
    corriendo.set()                          # arranca en marcha
    await asyncio.gather(trabajador_pausable(corriendo), control(corriendo))


async def main():
    global T0
    T0 = time.perf_counter()
    await pregunta_8()
    await pregunta_9()
    T0 = time.perf_counter()
    await pregunta_10()

asyncio.run(main())

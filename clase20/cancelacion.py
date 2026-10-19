#!/usr/bin/env python3
"""Ejercicio 5.2: cancelar lo que no cede, y tragarse la cancelación.

Uso:
    python3 cancelacion.py
"""
import asyncio
import time

DURACION = 3.0


def reloj(t0):
    return f'{time.perf_counter() - t0:4.2f}s'


async def calcular(t0, ceder):
    """Hace cuentas durante DURACION segundos. Si ceder, hace sleep(0) cada tanto."""
    print(f'    [{reloj(t0)}] tarea: arranco a calcular')
    try:
        fin = time.perf_counter() + DURACION
        vueltas = 0
        while time.perf_counter() < fin:
            sum(range(10_000))                   # trabajo de CPU
            vueltas += 1
            if ceder and vueltas % 100 == 0:
                await asyncio.sleep(0)           # paso el turno
        print(f'    [{reloj(t0)}] tarea: terminé de calcular')
        return 'resultado'
    except asyncio.CancelledError:
        print(f'    [{reloj(t0)}] tarea: recibí CancelledError')
        raise


async def intentar_cancelar(etiqueta, ceder):
    print(f'\n=== {etiqueta} ===')
    t0 = time.perf_counter()
    tarea = asyncio.create_task(calcular(t0, ceder))
    await asyncio.sleep(0.5)
    print(f'    [{reloj(t0)}] main: pido cancelar')
    pudo = tarea.cancel()
    print(f'    [{reloj(t0)}] main: cancel() devolvió {pudo}')
    try:
        resultado = await tarea
        print(f'    [{reloj(t0)}] main: la tarea devolvió {resultado!r}')
    except asyncio.CancelledError:
        print(f'    [{reloj(t0)}] main: la tarea quedó cancelada')


async def tragona(t0):
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print(f'    [{reloj(t0)}] tarea: me cancelaron... y me la trago')
    await asyncio.sleep(1)
    print(f'    [{reloj(t0)}] tarea: sigo como si nada')
    return 'sigo viva'


async def tragar_con_cancel():
    print('\n=== 7a: se traga el CancelledError (cancel + await) ===')
    t0 = time.perf_counter()
    tarea = asyncio.create_task(tragona(t0))
    await asyncio.sleep(0.5)
    print(f'    [{reloj(t0)}] main: pido cancelar')
    tarea.cancel()
    try:
        resultado = await tarea
        print(f'    [{reloj(t0)}] main: await devolvió {resultado!r}')
    except asyncio.CancelledError:
        print(f'    [{reloj(t0)}] main: la tarea quedó cancelada')
    print(f'    [{reloj(t0)}] main: tarea.cancelled() = {tarea.cancelled()}')


async def tragar_con_timeout():
    print('\n=== 7b: se traga el CancelledError (dentro de timeout(0.5)) ===')
    t0 = time.perf_counter()
    try:
        async with asyncio.timeout(0.5):
            resultado = await tragona(t0)
        print(f'    [{reloj(t0)}] main: el bloque terminó con {resultado!r}')
    except TimeoutError:
        print(f'    [{reloj(t0)}] main: TimeoutError')


async def main():
    await intentar_cancelar('6a: calcula sin ningún await', ceder=False)
    await intentar_cancelar('6b: calcula con sleep(0) cada tanto', ceder=True)
    await tragar_con_cancel()
    await tragar_con_timeout()


if __name__ == '__main__':
    asyncio.run(main())

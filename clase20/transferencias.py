#!/usr/bin/env python3
"""Ejercicio 4.2: race condition en asyncio cuando hay un await en el medio.

Uso:
    python3 transferencias.py
"""
import asyncio

SALDO_INICIAL = 1000
TRANSFERENCIAS = 100
MONTO = 1

cuentas = {}


async def transferir_sin_await(origen, destino, monto):
    saldo = cuentas[origen]
    cuentas[origen] = saldo - monto


async def transferir(origen, destino, monto):
    saldo = cuentas[origen]
    await asyncio.sleep(0)            # un punto de suspensión en el medio
    cuentas[origen] = saldo - monto


async def transferir_con_lock(lock, origen, destino, monto):
    async with lock:
        saldo = cuentas[origen]
        await asyncio.sleep(0)
        cuentas[origen] = saldo - monto


async def probar(etiqueta, hacer):
    cuentas.clear()
    cuentas.update({'A': SALDO_INICIAL, 'B': 0})
    await asyncio.gather(*(hacer('A', 'B', MONTO)
                           for _ in range(TRANSFERENCIAS)))
    esperado = SALDO_INICIAL - TRANSFERENCIAS * MONTO
    obtenido = cuentas['A']
    estado = 'OK' if obtenido == esperado else 'MAL'
    print(f'  {etiqueta:30} esperado {esperado:>5}  obtenido {obtenido:>5}  {estado}')


async def main():
    print(f'Cuenta A arranca en {SALDO_INICIAL}; '
          f'{TRANSFERENCIAS} transferencias de {MONTO}\n')

    await probar('sin await en el medio', transferir_sin_await)
    await probar('con await en el medio', transferir)

    lock = asyncio.Lock()
    await probar('con await + asyncio.Lock',
                 lambda o, d, m: transferir_con_lock(lock, o, d, m))

    print('\nUsando "with lock" en vez de "async with lock":')
    try:
        with lock:
            pass
    except Exception as e:
        print(f'  {type(e).__name__}: {e}')


if __name__ == '__main__':
    asyncio.run(main())

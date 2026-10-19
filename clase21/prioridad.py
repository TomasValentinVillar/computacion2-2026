import asyncio
import itertools


async def orden():
    print('=== PriorityQueue: sale primero la de menor número ===')
    cola = asyncio.PriorityQueue()
    await cola.put((3, 'baja'))
    await cola.put((1, 'urgente'))
    await cola.put((2, 'media'))
    while not cola.empty():
        print('  ', await cola.get())


async def empate_strings():
    print('\n=== Misma prioridad, items string ===')
    cola = asyncio.PriorityQueue()
    await cola.put((1, 'zeta'))
    await cola.put((1, 'alfa'))
    while not cola.empty():
        print('  ', await cola.get())


async def empate_dicts():
    print('\n=== Misma prioridad, items dict ===')
    cola = asyncio.PriorityQueue()
    try:
        await cola.put((1, {'url': 'a'}))
        await cola.put((1, {'url': 'b'}))
        print('   entraron las dos')
    except TypeError as e:
        print(f'   TypeError: {e}')


async def con_contador():
    print('\n=== Arreglo: (prioridad, contador, item) ===')
    cola = asyncio.PriorityQueue()
    contador = itertools.count()
    await cola.put((1, next(contador), {'url': 'b'}))
    await cola.put((1, next(contador), {'url': 'a'}))
    await cola.put((0, next(contador), {'url': 'urgente'}))
    while not cola.empty():
        print('  ', await cola.get())


async def main():
    await orden()
    await empate_strings()
    await empate_dicts()
    await con_contador()


asyncio.run(main())

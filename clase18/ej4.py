import asyncio

async def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f'  [{nombre}] paso {i}/{pasos}')
        await asyncio.sleep(0)          # ceder el control sin esperar nada

async def main():
    await asyncio.gather(
        tarea('A', 3),
        tarea('B', 2),
        tarea('C', 4),
    )

asyncio.run(main())

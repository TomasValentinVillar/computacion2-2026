import asyncio

async def cargar_configuracion():
    print('[init] cargando configuración...')
    await asyncio.sleep(2)                     # simula leer archivos, conectar a una base, etc.
    print('[init] configuración lista')

async def esperar_arranque(listo, nombre):
    print(f'[{nombre}] esperando que el sistema arranque...')
    await listo.wait()                         # se suspende hasta que alguien haga set()
    print(f'[{nombre}] ya puedo trabajar')
    await asyncio.sleep(0.5)                   # simula su trabajo
    print(f'[{nombre}] terminé')

async def inicializar(listo):
    await cargar_configuracion()
    listo.set()                                # despierta a todos los que esperan
    print('[init] evento seteado')

async def main():
    listo = asyncio.Event()

    await asyncio.gather(
        esperar_arranque(listo, 'servidor'),
        esperar_arranque(listo, 'logger'),
        esperar_arranque(listo, 'scheduler'),
        inicializar(listo),
    )

asyncio.run(main())
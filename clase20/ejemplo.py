#!/usr/bin/env python3
import asyncio

async def manejar(reader, writer):
    """Se ejecuta una vez por conexión, como el handle() de la clase 16."""
    direccion = writer.get_extra_info('peername')
    print(f'+ {direccion}')

    while True:
        datos = await reader.readline()
        datos = datos.upper()
        if not datos:
            break
        writer.write(datos)
        await writer.drain()

    print(f'- {direccion}')
    writer.close()
    await writer.wait_closed()

async def main():
    servidor = await asyncio.start_server(manejar, '0.0.0.0', 8080)
    async with servidor:
        print('largo server')
        await servidor.serve_forever()

asyncio.run(main())
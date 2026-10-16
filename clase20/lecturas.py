#!/usr/bin/env python3
"""Las formas de leer de un StreamReader, con el mismo mensaje."""
import asyncio

PUERTO = 8091
MENSAJE = b'hola\nmundo\n'


async def tras_cierre(reader):
    await reader.read()              # consumo todo hasta que el cliente cierra
    return await reader.read(100)    # y leo de nuevo


CASOS = [
    ('read(100)',                lambda r: r.read(100)),
    ('readline()',               lambda r: r.readline()),
    ('readexactly(4)',           lambda r: r.readexactly(4)),
    ("readuntil(b'\\n')",        lambda r: r.readuntil(b'\n')),
    ('readexactly(100)',         lambda r: r.readexactly(100)),
    ('read(100) tras el cierre', tras_cierre),
]


async def probar(nombre, leer):
    resultado = asyncio.get_running_loop().create_future()

    async def manejar(reader, writer):
        try:
            primero = await leer(reader)
            resto = await reader.read()          # lo que quedó, hasta EOF
            resultado.set_result((repr(primero), repr(resto)))
        except Exception as e:
            parcial = getattr(e, 'partial', None)
            texto = f'{type(e).__name__}: {e}'
            if parcial is not None:
                texto += f'  (partial={parcial!r})'
            resultado.set_result((texto, None))
        writer.close()
        await writer.wait_closed()

    srv = await asyncio.start_server(manejar, '127.0.0.1', PUERTO)
    async with srv:
        r, w = await asyncio.open_connection('127.0.0.1', PUERTO)
        w.write(MENSAJE)
        await w.drain()
        w.close()                                # mando y cierro
        await w.wait_closed()
        primero, resto = await resultado

    print(f'{nombre:26} -> {primero}')
    if resto is not None:
        print(f'{"":26}    quedó sin leer: {resto}')


async def main():
    print(f'El cliente manda {MENSAJE!r} y cierra.\n')
    for nombre, leer in CASOS:
        await probar(nombre, leer)


if __name__ == '__main__':
    asyncio.run(main())

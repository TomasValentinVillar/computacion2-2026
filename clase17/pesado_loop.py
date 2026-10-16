#!/usr/bin/env python3
"""Event loop con un handler que a veces hace trabajo pesado.

Uso:
    python3 pesado_loop.py
"""
import hashlib
import selectors
import socket

sel = selectors.DefaultSelector()


def trabajo_pesado(datos):
    h = datos
    for _ in range(3_000_000):        # ~2 segundos de CPU
        h = hashlib.sha256(h).digest()
    return h.hex().encode() + b'\n'


def aceptar(servidor):
    conn, direccion = servidor.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, atender)
    print(f'+ cliente {direccion}')


def atender(conn):
    try:
        datos = conn.recv(4096)
    except ConnectionResetError:
        datos = b''
    if not datos:
        sel.unregister(conn)
        conn.close()
        return
    if datos.startswith(b'pesado'):
        print('  calculando...')
        respuesta = trabajo_pesado(datos)
        print('  listo')
    else:
        respuesta = datos
    conn.sendall(respuesta)           # respuestas chicas: entran en el buffer


servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
servidor.bind(('0.0.0.0', 8080))
servidor.listen(128)
servidor.setblocking(False)
sel.register(servidor, selectors.EVENT_READ, aceptar)
print('Event loop en :8080')

try:
    while True:
        for clave, _ in sel.select():
            clave.data(clave.fileobj)
except KeyboardInterrupt:
    print('\nServidor detenido')

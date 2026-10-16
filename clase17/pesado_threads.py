#!/usr/bin/env python3
"""Thread por cliente con el mismo trabajo pesado.

Uso:
    python3 pesado_threads.py
"""
import hashlib
import socketserver


def trabajo_pesado(datos):
    h = datos
    for _ in range(3_000_000):
        h = hashlib.sha256(h).digest()
    return h.hex().encode() + b'\n'


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        while True:
            datos = self.request.recv(4096)
            if not datos:
                return
            if datos.startswith(b'pesado'):
                print('  calculando...')
                respuesta = trabajo_pesado(datos)
                print('  listo')
            else:
                respuesta = datos
            self.request.sendall(respuesta)


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


with Servidor(('0.0.0.0', 8080), Handler) as srv:
    print('Threads en :8080')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido')

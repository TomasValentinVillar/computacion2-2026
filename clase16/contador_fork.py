#!/usr/bin/env python3
"""Contador de visitas con ForkingTCPServer.

Uso:
    python3 contador_fork.py            # contador común (roto)
    python3 contador_fork.py --value    # con multiprocessing.Value
"""
import multiprocessing
import os
import socketserver
import sys


class Contador(socketserver.StreamRequestHandler):
    def handle(self):
        if self.server.usar_value:
            with self.server.visitas.get_lock():
                self.server.visitas.value += 1
                n = self.server.visitas.value
        else:
            self.server.visitas += 1
            n = self.server.visitas
        print(f'  hijo pid={os.getpid()} -> visita {n}')
        self.wfile.write(f'visita {n}\n'.encode())


class Servidor(socketserver.ForkingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, usar_value=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.usar_value = usar_value
        if usar_value:
            self.visitas = multiprocessing.Value('i', 0)
        else:
            self.visitas = 0


if __name__ == '__main__':
    usar_value = '--value' in sys.argv
    modo = 'multiprocessing.Value' if usar_value else 'int común'
    with Servidor(('localhost', 8080), Contador, usar_value=usar_value) as srv:
        print(f'Padre pid={os.getpid()} — contador con {modo}')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            final = srv.visitas.value if usar_value else srv.visitas
            print(f'\nEl PADRE cree que hubo {final} visitas')

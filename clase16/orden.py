#!/usr/bin/env python3
"""Servidor lento para comparar Bien vs Mal.

Uso:
    python3 orden.py bien
    python3 orden.py mal
"""
import socketserver
import sys
import threading
import time


class Lento(socketserver.StreamRequestHandler):
    def handle(self):
        print(f'atiendo {self.client_address} en {threading.current_thread().name}')
        time.sleep(3)
        self.wfile.write(b'listo\n')


class Bien(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Mal(socketserver.TCPServer, socketserver.ThreadingMixIn):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    Clase = Bien if sys.argv[1] == 'bien' else Mal
    with Clase(('localhost', 8080), Lento) as srv:
        print(f'Servidor {Clase.__name__} en localhost:8080')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor detenido')

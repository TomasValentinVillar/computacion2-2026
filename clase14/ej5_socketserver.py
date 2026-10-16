#!/usr/bin/env python3
"""Servidor eco con socketserver.
Uso: python3 ej5_socketserver.py [--lento S] [--forking]
"""
import socketserver
import sys
import time

LENTO = float(sys.argv[sys.argv.index('--lento') + 1]) if '--lento' in sys.argv else 0.0
FORKING = '--forking' in sys.argv


class EchoHandler(socketserver.StreamRequestHandler):
    def handle(self):
        """Se llama una vez por conexion, en su propio thread (o proceso)."""
        if LENTO:
            time.sleep(LENTO)
        while True:
            datos = self.rfile.read1(4096)   # lo que haya, sin esperar '\n'
            if not datos:
                break
            self.wfile.write(datos)


Base = socketserver.ForkingTCPServer if FORKING else socketserver.ThreadingTCPServer


class Servidor(Base):
    allow_reuse_address = True
    daemon_threads = True          # solo afecta al de threads
    request_queue_size = 1024      # el backlog de listen()


if __name__ == '__main__':
    with Servidor(('0.0.0.0', 8080), EchoHandler) as srv:
        print(f'[socketserver {"FORKING" if FORKING else "THREADING"}] '
              f'escuchando en 0.0.0.0:8080'
              f'{f" (lento: {LENTO}s)" if LENTO else ""}')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor detenido')

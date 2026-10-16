#!/usr/bin/env python3
"""Qué pasa al cortar el servidor con un cliente conectado.

Uso:
    python3 daemon.py               # daemon_threads = True
    python3 daemon.py --sin-daemon  # daemon_threads = False
"""
import socketserver
import sys
import threading


class Eco(socketserver.StreamRequestHandler):
    def handle(self):
        print(f'+ {self.client_address} en {threading.current_thread().name}')
        for linea in self.rfile:
            self.wfile.write(linea)
        print(f'- {self.client_address} cerró')


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = '--sin-daemon' not in sys.argv


if __name__ == '__main__':
    with Servidor(('localhost', 8080), Eco) as srv:
        print(f'daemon_threads = {Servidor.daemon_threads}')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nCtrl+C recibido, cerrando...')
    print('Proceso terminado')

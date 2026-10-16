#!/usr/bin/env python3
"""Handler UDP lento: secuencial vs con threads.

Uso:
    python3 udp_lento.py            # UDPServer
    python3 udp_lento.py --threads  # ThreadingUDPServer
"""
import socketserver
import sys
import threading
import time


class Lento(socketserver.BaseRequestHandler):
    def handle(self):
        datos, sock = self.request
        print(f'atiendo {datos!r} de {self.client_address} '
              f'en {threading.current_thread().name}')
        time.sleep(3)
        sock.sendto(b'listo ' + datos, self.client_address)


if __name__ == '__main__':
    Base = socketserver.ThreadingUDPServer if '--threads' in sys.argv else socketserver.UDPServer

    class Servidor(Base):
        allow_reuse_address = True
        daemon_threads = True

    with Servidor(('localhost', 8080), Lento) as srv:
        print(f'Servidor {Base.__name__} en localhost:8080')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor detenido')

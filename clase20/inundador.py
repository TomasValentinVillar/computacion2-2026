#!/usr/bin/env python3
"""Manda 100 MB al servidor eco y NUNCA lee la respuesta."""
import socket
import time

MB = 100
linea = b'x' * 1023 + b'\n'          # 1 KB por línea

s = socket.create_connection(('localhost', 8080))
enviado = 0
for _ in range(MB * 1024):
    s.sendall(linea)
    enviado += len(linea)
    if enviado % (10 * 1024 * 1024) == 0:
        print(f'enviados {enviado // (1024 * 1024)} MB', flush=True)

print('terminé de mandar; me quedo sin leer nada...', flush=True)
time.sleep(3600)

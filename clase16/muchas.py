#!/usr/bin/env python3
"""Abre N conexiones simultáneas y las mantiene abiertas.

Uso:
    python3 muchas.py 200
"""
import socket
import sys
import time

n = int(sys.argv[1])
conexiones = []
inicio = time.time()

try:
    for i in range(n):
        conexiones.append(socket.create_connection(('localhost', 8080)))
        if (i + 1) % 100 == 0:
            print(f'{i + 1} conexiones abiertas')
except OSError as e:
    print(f'\nFalló en la conexión {len(conexiones) + 1}: {e!r}')

print(f'{len(conexiones)} abiertas en {time.time() - inicio:.2f}s')
input('Enter para cerrar todas...')
for s in conexiones:
    s.close()

#!/usr/bin/env python3
"""Manda DISCOVER? por broadcast y junta las respuestas.

Uso: python3 broadcast_cliente.py            # con SO_BROADCAST
     python3 broadcast_cliente.py sin-flag   # sin la proteccion
"""
import socket
import sys

sin_flag = len(sys.argv) > 1 and sys.argv[1] == 'sin-flag'

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
if not sin_flag:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.settimeout(2.0)

try:
    s.sendto(b'DISCOVER?', ('255.255.255.255', 8082))
except OSError as e:
    print(f'Error al enviar: {type(e).__name__}: {e}')
    sys.exit(1)

respuestas = 0
try:
    while True:
        datos, origen = s.recvfrom(4096)
        respuestas += 1
        print(f'{origen} respondio: {datos!r}')
except TimeoutError:
    pass
print(f'\n{respuestas} maquina(s) respondieron')

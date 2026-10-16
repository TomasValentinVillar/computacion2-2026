#!/usr/bin/env python3
"""Servidor dual-stack: imprime la dirección que ve de cada cliente.

Uso:
    python3 dual.py 0     # IPV6_V6ONLY=0: acepta IPv6 e IPv4
    python3 dual.py 1     # IPV6_V6ONLY=1: solo IPv6
"""
import socket
import sys

v6only = int(sys.argv[1]) if len(sys.argv) > 1 else 0

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, v6only)
s.bind(('::', 8080))
s.listen(5)
print(f'Escuchando en [::]:8080 con IPV6_V6ONLY={v6only}')

try:
    while True:
        conn, direccion = s.accept()
        print('cliente:', direccion)
        conn.close()
except KeyboardInterrupt:
    print('\nServidor detenido')
finally:
    s.close()

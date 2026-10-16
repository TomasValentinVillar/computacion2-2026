#!/usr/bin/env python3
"""Manda 10 MB con UN solo send() y muestra cuántos bytes mandó realmente."""
import socket

with socket.create_connection(('localhost', 8080), timeout=5) as s:
    datos = b'x' * (10 * 1024 * 1024)      # 10 MB de bytes
    print(f'Voy a mandar: {len(datos)} bytes')
    n = s.send(datos)                       # UNA sola llamada, sin loop
    print(f'send() devolvió: {n} bytes')
    print(f'¿Mandó todo? {n == len(datos)}')
    print(f'Quedaron sin mandar: {len(datos) - n} bytes')
#!/usr/bin/env python3
"""Responde a DISCOVER? con el nombre de la maquina."""
import socket

PUERTO = 8082

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', PUERTO))                 # '' = todas las interfaces
    nombre = socket.gethostname()
    print(f'Esperando DISCOVER? en el puerto {PUERTO} (soy {nombre})')
    while True:
        datos, origen = s.recvfrom(65535)
        print(f'  de {origen[0]}:{origen[1]}: {datos!r}')
        if datos == b'DISCOVER?':
            # la respuesta va solo al que pregunto, no en broadcast
            s.sendto(f'aca estoy: {nombre}'.encode(), origen)

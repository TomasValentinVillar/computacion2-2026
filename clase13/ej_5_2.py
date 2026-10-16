#!/usr/bin/env python3
import socket

with socket.create_connection(('localhost', 8080)) as s:
    s.settimeout(3)           # límite de 3 segundos para operaciones bloqueantes
    print('Conectado. Intento recibir con timeout de 3s...')
    try:
        datos = s.recv(4096)
        print(f'Recibí: {datos!r}')
    except TimeoutError:
        print('El servidor no respondió en 3 segundos')
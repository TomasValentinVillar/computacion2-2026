#!/usr/bin/env python3
import socket

with socket.create_connection(('localhost', 8080)) as s:
    s.sendall(b'test\n')
    while True:
        datos = s.recv(4096)
        if not datos:              # <-- el chequeo que faltaba
            print('El servidor cerró la conexión')
            break                  # salgo del loop
        print(f'recv devolvió: {datos!r}')
#!/usr/bin/env python3
from protocolo_c import enviar_mensaje, recibir_mensaje
import socket



with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('localhost', 8080))
    servidor.listen(5)
    print('Escuchando en localhost:8080...')
    while True:
        conn, direccion = servidor.accept()
        print(f'Conexión desde {direccion}')
        with conn:
            while True:
                mensaje = recibir_mensaje(conn)
                if mensaje is None:
                    break
                print(f'Recibí ({len(mensaje)} bytes): {mensaje!r}')
                enviar_mensaje(conn, mensaje.upper())
        print('Conexión cerrada')
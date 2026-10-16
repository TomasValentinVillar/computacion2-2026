#!/usr/bin/env python3
import socket
from protocolo_c import enviar_mensaje, recibir_mensaje

with socket.create_connection(('localhost', 8080), timeout=5) as s:
    mensaje = b'hola\ncomo\nestas'      # tiene \n adentro
    enviar_mensaje(s, mensaje)
    respuesta = recibir_mensaje(s)
    print(f'Envié {mensaje!r}')
    print(f'Recibí {respuesta!r}')
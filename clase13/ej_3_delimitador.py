#!/usr/bin/env python3
"""Servidor con framing por líneas."""
import socket

def recibir_lineas(sock):
    """Generador de líneas completas.
    PISTA: necesitás un buffer que sobreviva entre llamadas a recv().
    Un recv() puede traer media línea, o tres líneas y media."""
    buffer = b''
    while True:
        pedazo = sock.recv(4096)
        if not pedazo:
            return
        # acumular en el buffer y entregar TODAS las líneas completas
        buffer += pedazo
        while b'\n' in buffer:
            linea, buffer = buffer.split(b'\n', 1)
            yield linea

# servidor que use recibir_lineas() y responda en mayúsculas
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('localhost', 8080))
    servidor.listen(5)
    print('Escuchando en localhost:8080...')
    while True:
        conn, direccion = servidor.accept()
        print(f'Conexión desde {direccion}')
        with conn:
            for linea in recibir_lineas(conn):
                print(f'Recibí: {linea!r}')
                conn.sendall(linea.upper() + b'\n')     # respuesta en mayúsculas, terminada en \n
        print('Conexión cerrada')
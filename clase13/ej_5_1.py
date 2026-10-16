#!/usr/bin/env python3
"""Cliente que reintenta conectar con backoff hasta que el servidor aparezca."""
import socket
import time

def conectar_con_reintentos(host, puerto, intentos=5):
    for intento in range(1, intentos + 1):
        try:
            return socket.create_connection((host, puerto), timeout=2)
        except (ConnectionRefusedError, TimeoutError) as e:
            espera = 0.5 * intento          # backoff: espera creciente
            print(f'Intento {intento} falló ({e}). Reintento en {espera}s')
            time.sleep(espera)
    raise ConnectionError(f'No se pudo conectar a {host}:{puerto} tras {intentos} intentos')

if __name__ == '__main__':
    s = conectar_con_reintentos('localhost', 8080)
    print('¡Conectado!')
    with s:
        s.sendall(b'hola\n')
        print(s.recv(4096))
#!/usr/bin/env python3
"""server_threads.py SIN lock, para provocar la race condition.
Uso: python3 ej4_sin_lock.py [--lento S] [--race]
--race mete un sleep entre la lectura y la escritura del contador.
"""
import socket
import sys
import threading
import time

HOST = '0.0.0.0'
PUERTO = 8080
LENTO = float(sys.argv[sys.argv.index('--lento') + 1]) if '--lento' in sys.argv else 0.0
RACE = '--race' in sys.argv

clientes_activos = 0
pico_simultaneos = 0


def atender(conn, direccion):
    global clientes_activos, pico_simultaneos
    # SIN lock: lectura y escritura separadas
    valor = clientes_activos
    if RACE:
        time.sleep(0.0001)
    clientes_activos = valor + 1
    pico_simultaneos = max(pico_simultaneos, clientes_activos)
    try:
        if LENTO:
            time.sleep(LENTO)
        with conn:
            while True:
                datos = conn.recv(4096)
                if not datos:
                    break
                conn.sendall(datos)
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        valor = clientes_activos
        if RACE:
            time.sleep(0.0001)
        clientes_activos = valor - 1


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PUERTO))
        servidor.listen(1024)
        print(f'[threads SIN LOCK] escuchando en {HOST}:{PUERTO}'
              f'{" (race activado)" if RACE else ""}')
        while True:
            conn, direccion = servidor.accept()
            threading.Thread(target=atender, args=(conn, direccion),
                             daemon=True).start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f'\nServidor detenido. Pico: {pico_simultaneos}  '
              f'Activos al final: {clientes_activos}  (deberia ser 0)')

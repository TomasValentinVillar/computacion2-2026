#!/usr/bin/env python3
"""Servidor eco con threads + trabajo CPU-bound real."""
import socket
import threading


def trabajo_cpu(n=2_000_000):
    """CPU-bound de verdad: no libera el GIL."""
    total = 0
    for i in range(n):
        total += i * i
    return total


def atender(conn):
    try:
        trabajo_cpu()
        with conn:
            while True:
                datos = conn.recv(4096)
                if not datos:
                    break
                conn.sendall(datos)
    except (ConnectionResetError, BrokenPipeError):
        pass


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', 8080))
    servidor.listen(128)
    print('[threads CPU] escuchando en 0.0.0.0:8080')
    try:
        while True:
            conn, _ = servidor.accept()
            threading.Thread(target=atender, args=(conn,), daemon=True).start()
    except KeyboardInterrupt:
        print('\nServidor detenido')

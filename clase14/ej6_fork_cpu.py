#!/usr/bin/env python3
"""Servidor eco con fork + trabajo CPU-bound real."""
import os
import signal
import socket


def trabajo_cpu(n=2_000_000):
    """CPU-bound de verdad: no libera el GIL."""
    total = 0
    for i in range(n):
        total += i * i
    return total


def atender(conn):
    trabajo_cpu()
    while True:
        datos = conn.recv(4096)
        if not datos:
            break
        conn.sendall(datos)


signal.signal(signal.SIGCHLD, signal.SIG_IGN)   # el kernel cosecha (Parte D)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', 8080))
    servidor.listen(128)
    print(f'[fork CPU] PADRE pid={os.getpid()} escuchando en 0.0.0.0:8080')
    try:
        while True:
            conn, _ = servidor.accept()
            if os.fork() == 0:
                servidor.close()
                try:
                    atender(conn)
                except (ConnectionResetError, BrokenPipeError):
                    pass
                finally:
                    conn.close()
                    os._exit(0)
            conn.close()
    except KeyboardInterrupt:
        print('\nServidor detenido')

#!/usr/bin/env python3
"""Ejercicio 4: que hace connect() en un socket UDP."""
import socket
import time

VACIO = ('localhost', 9999)          # puerto donde no hay nadie


def con_connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.connect(VACIO)
    s.send(b'hola')
    t = time.monotonic()
    try:
        s.recv(4096)
        r = 'llego respuesta (?)'
    except ConnectionRefusedError:
        r = 'ConnectionRefusedError'
    except TimeoutError:
        r = 'timeout'
    print(f'CON connect: {r:<24} en {time.monotonic() - t:.3f}s')
    s.close()


def sin_connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.sendto(b'hola', VACIO)
    t = time.monotonic()
    try:
        s.recvfrom(4096)
        r = 'llego respuesta (?)'
    except ConnectionRefusedError:
        r = 'ConnectionRefusedError'
    except TimeoutError:
        r = 'timeout'
    print(f'SIN connect: {r:<24} en {time.monotonic() - t:.3f}s')
    s.close()


def filtro(usar_connect):
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(('127.0.0.1', 46021))
    amigo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    amigo.bind(('127.0.0.1', 46002))
    extrano = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if usar_connect:
        rx.connect(('127.0.0.1', 46002))     # solo acepto al amigo

    extrano.sendto(b'soy un extrano', ('127.0.0.1', 46021))
    amigo.sendto(b'soy el amigo', ('127.0.0.1', 46021))

    rx.settimeout(1)
    titulo = 'CON connect' if usar_connect else 'SIN connect'
    print(f'\n{titulo} al amigo (46002):')
    try:
        while True:
            datos, origen = rx.recvfrom(4096)
            print(f'   recibido de {origen[1]}: {datos}')
    except TimeoutError:
        print('   (no llego nada mas)')
    for s in (rx, amigo, extrano):
        s.close()


if __name__ == '__main__':
    print('--- Puerto vacio ---')
    con_connect()
    sin_connect()
    print('\n--- Filtro de remitentes ---')
    filtro(usar_connect=False)
    filtro(usar_connect=True)

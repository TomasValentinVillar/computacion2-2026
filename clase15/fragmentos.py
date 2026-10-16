#!/usr/bin/env python3
"""Ejercicio 6: cuantos datagramas llegan completos segun su tamano.

Uso: python3 fragmentos.py [tamano] [cantidad] [perdida_para_calculo]
"""
import socket
import struct
import sys
import threading
import time

PUERTO = 8083


def mtu_lo():
    with open('/sys/class/net/lo/mtu') as f:
        return int(f.read())


def receptor(tam, recibidos, listo):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as r:
        r.bind(('127.0.0.1', PUERTO))
        listo.set()
        r.settimeout(2.0)
        while True:
            try:
                datos, _ = r.recvfrom(65535)
            except TimeoutError:
                return
            if len(datos) == tam:
                recibidos.append(struct.unpack('!I', datos[:4])[0])


def main():
    tam = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    p = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05

    mtu = mtu_lo()
    if tam + 28 <= mtu:
        frags = 1
    else:
        por_frag = (mtu - 20) // 8 * 8       # payload IP por fragmento
        frags = -(-(tam + 8) // por_frag)    # division hacia arriba

    print(f'MTU de lo: {mtu}   datagrama: {tam} bytes   '
          f'fragmentos: {frags}')
    print(f'Probabilidad teorica de llegar entero con {p:.0%} de perdida: '
          f'(1 - {p})^{frags} = {(1 - p) ** frags:.1%}\n')

    recibidos = []
    listo = threading.Event()
    hilo = threading.Thread(target=receptor, args=(tam, recibidos, listo))
    hilo.start()
    listo.wait()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for i in range(n):
            datos = struct.pack('!I', i) + b'X' * (tam - 4)
            try:
                s.sendto(datos, ('127.0.0.1', PUERTO))
            except OSError as e:
                print(f'Error al enviar: {type(e).__name__}: {e}')
                break
            time.sleep(0.05)        # no llenar el buffer del receptor

    hilo.join()
    print(f'Llegaron completos: {len(recibidos)} de {n}')


if __name__ == '__main__':
    main()

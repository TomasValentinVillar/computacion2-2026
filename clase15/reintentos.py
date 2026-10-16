#!/usr/bin/env python3
"""Ejercicio 3 B: cliente con reintentos contra un eco con pérdidas.

Uso: python3 reintentos.py [prob] [timeout]
"""
import random
import socket
import sys
import threading
import time

PUERTO = 8096
LATENCIA = 0.05      # 50 ms de "red" (en localhost real seria ~0)
N = 10               # mensajes a enviar

trabajo = [0]        # cuantas veces el servidor hizo el trabajo real


def sendto_con_perdidas(sock, datos, destino, prob):
    if random.random() < prob:
        return len(datos)                    # miente: no manda
    return sock.sendto(datos, destino)


def servidor(prob, listo):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('localhost', PUERTO))
    listo.set()
    while True:
        datos, origen = s.recvfrom(65535)
        trabajo[0] += 1                      # el trabajo real
        respuesta = datos.upper()
        # la respuesta sale con LATENCIA de demora, sin trabar el bucle
        threading.Timer(LATENCIA, sendto_con_perdidas,
                        args=(s, respuesta, origen, prob)).start()


def pedir_con_reintentos(sock, mensaje, destino, prob, intentos=5, timeout=0.5):
    """Manda y reintenta si no llega respuesta."""
    sock.settimeout(timeout)
    for intento in range(1, intentos + 1):
        sendto_con_perdidas(sock, mensaje, destino, prob)
        try:
            respuesta, _ = sock.recvfrom(65535)
            return respuesta, intento
        except TimeoutError:
            pass                             # silencio: reintento
    return None, intentos


def main():
    prob = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    listo = threading.Event()
    threading.Thread(target=servidor, args=(prob, listo), daemon=True).start()
    listo.wait()

    print(f'Perdida {prob:.0%} por direccion, timeout {timeout}s, '
          f'latencia {LATENCIA * 1000:.0f}ms\n')

    ok = fallidos = equivocadas = total_intentos = 0
    inicio = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for i in range(N):
            msg = f'msg{i}'.encode()
            resp, n = pedir_con_reintentos(s, msg, ('localhost', PUERTO),
                                           prob, timeout=timeout)
            total_intentos += n
            if resp is None:
                fallidos += 1
                estado = 'SIN RESPUESTA'
            elif resp != msg.upper():
                equivocadas += 1
                estado = f'{resp.decode()}   <-- EQUIVOCADA'
            else:
                ok += 1
                estado = resp.decode()
            print(f'  {msg.decode():<6} -> {estado}  ({n} intento/s)')

    duracion = time.time() - inicio
    time.sleep(LATENCIA * 3)                 # dejar terminar lo que viaja

    print(f'\nCorrectas: {ok}   Equivocadas: {equivocadas}   Fallidas: {fallidos}')
    print(f'Intentos promedio por mensaje: {total_intentos / N:.2f}')
    print(f'Tiempo total: {duracion:.2f}s')
    print(f'Veces que el servidor hizo el trabajo: {trabajo[0]} '
          f'(mensajes reales: {N})')


if __name__ == '__main__':
    main()

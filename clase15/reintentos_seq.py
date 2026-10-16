#!/usr/bin/env python3
"""Ejercicio 3 D: reintentos + numeros de secuencia.

Uso: python3 reintentos_seq.py [prob] [timeout]
"""
import random
import socket
import struct
import sys
import threading
import time

PUERTO = 8095
LATENCIA = 0.05
N = 10

trabajo = [0]
descartadas = [0]


def empaquetar(seq, payload):
    return struct.pack('!I', seq) + payload


def desempaquetar(datos):
    (seq,) = struct.unpack('!I', datos[:4])
    return seq, datos[4:]


def sendto_con_perdidas(sock, datos, destino, prob):
    if random.random() < prob:
        return len(datos)
    return sock.sendto(datos, destino)


def servidor(prob, listo):
    vistos = {}                              # (origen, seq) -> respuesta
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('localhost', PUERTO))
    listo.set()
    while True:
        datos, origen = s.recvfrom(65535)
        seq, payload = desempaquetar(datos)
        clave = (origen, seq)
        if clave in vistos:
            respuesta = vistos[clave]        # duplicado: no trabajo
        else:
            trabajo[0] += 1                  # nuevo: trabajo real, una vez
            respuesta = payload.upper()
            vistos[clave] = respuesta
        threading.Timer(LATENCIA, sendto_con_perdidas,
                        args=(s, empaquetar(seq, respuesta), origen, prob)).start()


def pedir(sock, seq, payload, destino, prob, intentos=5, timeout=0.5):
    for intento in range(1, intentos + 1):
        sendto_con_perdidas(sock, empaquetar(seq, payload), destino, prob)
        limite = time.monotonic() + timeout
        while True:
            restante = limite - time.monotonic()
            if restante <= 0:
                break
            sock.settimeout(restante)
            try:
                datos, _ = sock.recvfrom(65535)
            except TimeoutError:
                break
            seq_resp, respuesta = desempaquetar(datos)
            if seq_resp == seq:
                return respuesta, intento
            descartadas[0] += 1              # respuesta vieja: la ignoro
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
        for seq in range(N):
            msg = f'msg{seq}'.encode()
            resp, n = pedir(s, seq, msg, ('localhost', PUERTO),
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
            print(f'  seq={seq} {msg.decode():<6} -> {estado}  ({n} intento/s)')

    duracion = time.time() - inicio
    time.sleep(LATENCIA * 3)

    print(f'\nCorrectas: {ok}   Equivocadas: {equivocadas}   Fallidas: {fallidos}')
    print(f'Intentos promedio por mensaje: {total_intentos / N:.2f}')
    print(f'Respuestas viejas descartadas por seq: {descartadas[0]}')
    print(f'Tiempo total: {duracion:.2f}s')
    print(f'Veces que el servidor hizo el trabajo: {trabajo[0]} '
          f'(mensajes reales: {N})')


if __name__ == '__main__':
    main()

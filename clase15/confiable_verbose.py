#!/usr/bin/env python3
"""confiable.py narrado: muestra qué pasa en cada intento."""
import random
import socket
import struct
import sys
import threading
import time

PUERTO = 8097


def empaquetar(seq, payload):
    return struct.pack('!I', seq) + payload


def desempaquetar(datos):
    (seq,) = struct.unpack('!I', datos[:4])
    return seq, datos[4:]


def enviar_con_perdidas(sock, datos, destino, prob, que):
    seq, _ = desempaquetar(datos)
    if random.random() < prob:
        print(f'      [red] {que} seq={seq} -> SE PERDIO')
        return
    print(f'      [red] {que} seq={seq} -> viajo bien')
    sock.sendto(datos, destino)


def servidor(prob, listo, fin):
    vistos = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', PUERTO))
        listo.set()
        s.settimeout(0.5)
        while not fin.is_set():
            try:
                datos, origen = s.recvfrom(65535)
            except TimeoutError:
                continue
            seq, payload = desempaquetar(datos)
            if seq in vistos:
                print(f'      [servidor] seq={seq} REPETIDO: no trabajo, '
                      f'reenvio lo guardado')
                respuesta = vistos[seq]
            else:
                print(f'      [servidor] seq={seq} nuevo: HAGO EL TRABAJO')
                respuesta = payload.upper()
                vistos[seq] = respuesta
            enviar_con_perdidas(s, empaquetar(seq, respuesta), origen,
                                prob, 'respuesta')


def pedir(sock, seq, payload, destino, prob, intentos=8, timeout=0.3):
    sock.settimeout(timeout)
    for intento in range(1, intentos + 1):
        print(f'   [cliente] intento {intento}: mando seq={seq}')
        enviar_con_perdidas(sock, empaquetar(seq, payload), destino,
                            prob, 'pedido')
        try:
            datos, _ = sock.recvfrom(65535)
        except TimeoutError:
            print(f'   [cliente] silencio 0.3s... reintento')
            continue
        seq_resp, respuesta = desempaquetar(datos)
        if seq_resp == seq:
            print(f'   [cliente] recibi la respuesta de seq={seq}')
            return respuesta, intento
        print(f'   [cliente] llego seq={seq_resp} viejo, lo descarto')
    print(f'   [cliente] me rindo con seq={seq}')
    return None, intentos


def main():
    prob = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    mensajes = [b'hola', b'que', b'tal']

    listo, fin = threading.Event(), threading.Event()
    hilo = threading.Thread(target=servidor, args=(prob, listo, fin))
    hilo.start()
    listo.wait()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for seq, msg in enumerate(mensajes):
            print(f'\n=== {msg.decode()} (seq={seq}) ===')
            respuesta, n = pedir(s, seq, msg, ('localhost', PUERTO), prob)
            estado = respuesta.decode() if respuesta else 'SIN RESPUESTA'
            print(f'=== resultado: {estado} en {n} intento(s)')
            time.sleep(0.05)

    fin.set()
    hilo.join()


if __name__ == '__main__':
    main()

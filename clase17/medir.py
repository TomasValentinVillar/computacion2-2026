#!/usr/bin/env python3
"""A pide trabajo pesado; B, un poco después, pide un eco liviano."""
import socket
import threading
import time


def cliente(nombre, mensaje, demora):
    time.sleep(demora)
    with socket.create_connection(('localhost', 8080)) as s:
        t = time.time()
        s.sendall(mensaje)
        s.recv(4096)
        print(f'{nombre}: respuesta a los {time.time() - inicio:.1f}s '
              f'(esperó {time.time() - t:.1f}s)')


inicio = time.time()
hilos = [threading.Thread(target=cliente, args=('A (pesado)', b'pesado', 0)),
         threading.Thread(target=cliente, args=('B (hola)  ', b'hola', 0.3))]
for h in hilos:
    h.start()
for h in hilos:
    h.join()

#!/usr/bin/env python3
"""Dos clientes UDP simultáneos, midiendo el tiempo total."""
import socket
import threading
import time


def cliente(i):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(10)
        s.sendto(f'cliente {i}'.encode(), ('localhost', 8080))
        respuesta, _ = s.recvfrom(65535)
        print(f'{respuesta.decode()} a los {time.time() - inicio:.1f}s')


inicio = time.time()
hilos = [threading.Thread(target=cliente, args=(i,)) for i in range(2)]
for h in hilos:
    h.start()
for h in hilos:
    h.join()
print(f'Total: {time.time() - inicio:.1f}s')

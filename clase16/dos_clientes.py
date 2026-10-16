#!/usr/bin/env python3
"""Abre dos conexiones a la vez y mide el tiempo total."""
import socket
import threading
import time


def cliente(i):
    with socket.create_connection(('localhost', 8080)) as s:
        s.recv(100)
        print(f'cliente {i} terminó a los {time.time() - inicio:.1f}s')


inicio = time.time()
hilos = [threading.Thread(target=cliente, args=(i,)) for i in range(2)]
for h in hilos:
    h.start()
for h in hilos:
    h.join()
print(f'Total: {time.time() - inicio:.1f}s')

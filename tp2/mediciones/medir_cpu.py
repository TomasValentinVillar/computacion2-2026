#!/usr/bin/env python3
"""Medición 2: ¿el event loop se bloquea con una tarea CPU-bound?

Manda N tareas `hashear` a la vez y, mientras corren, hace GET /tareas cada
0.1 s midiendo cuánto tarda en responder. Al final reporta:
- el tiempo total hasta que terminan todas las tareas
- la latencia del GET (promedio y peor caso) mientras había hashes corriendo

Uso (con el servidor ya levantado en el MODO_CPU que se quiera medir):
    python3 medir_cpu.py [cantidad] [iteraciones]
"""
import json
import statistics
import sys
import threading
import time
import urllib.request

URL = 'http://localhost:8000'
CANTIDAD = int(sys.argv[1]) if len(sys.argv) > 1 else 4
ITERACIONES = int(sys.argv[2]) if len(sys.argv) > 2 else 5_000_000


def pedir(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo else None
    req = urllib.request.Request(URL + ruta, data=datos, method=metodo,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def sondear(latencias, terminar):
    """Hace GET /tareas cada 0.1 s y anota cuánto tardó cada uno."""
    while not terminar.is_set():
        t0 = time.perf_counter()
        pedir('GET', '/tareas')
        latencias.append(time.perf_counter() - t0)
        time.sleep(0.1)


def main():
    latencias, terminar = [], threading.Event()
    t0 = time.perf_counter()
    ids = [pedir('POST', '/tareas', {
        'tipo': 'hashear', 'timeout': 120,
        'parametros': {'texto': f'medicion {i}', 'iteraciones': ITERACIONES},
    })['id'] for i in range(CANTIDAD)]

    sonda = threading.Thread(target=sondear, args=(latencias, terminar))
    sonda.start()
    while not all(pedir('GET', f'/tareas/{i}')['estado'] == 'completada' for i in ids):
        time.sleep(0.2)
    total = time.perf_counter() - t0
    terminar.set()
    sonda.join()

    print(f'{CANTIDAD} hashes de {ITERACIONES:,} iteraciones')
    print(f'  tiempo total:            {total:6.2f} s')
    print(f'  GET /tareas durante:     {len(latencias)} pedidos')
    print(f'    latencia promedio:     {statistics.mean(latencias) * 1000:8.1f} ms')
    print(f'    latencia peor caso:    {max(latencias) * 1000:8.1f} ms')


if __name__ == '__main__':
    main()

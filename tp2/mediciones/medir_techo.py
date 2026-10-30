#!/usr/bin/env python3
"""Medición 3: el techo del pool. ¿Hasta cuántas tareas concurrentes aguanta?

Para cada N levanta el servidor con N_WORKERS = N (que no falten workers),
manda N tareas iguales a la vez (desde 32 hilos, para que mandar no tarde más
que ejecutar) y mide con los timestamps del propio sistema:
- total: desde la primera `creada` hasta la última `finalizada`
- ejecución promedio y peor: si el loop está saturado, una tarea de 1 s tarda más
- latencia de GET /estadisticas con todas las tareas en curso
- memoria del servidor (VmRSS de /proc/<pid>/status, como en el TP1)

Uso (desde tp2/src):
    python3 ../mediciones/medir_techo.py cpu 1 4 8 16 32
    python3 ../mediciones/medir_techo.py io 10 100 1000 10000
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = 'http://localhost:8000'
TAREA = {
    'cpu': {'tipo': 'hashear', 'timeout': 300,
            'parametros': {'texto': 'techo', 'iteraciones': 2_000_000}},
    'io': {'tipo': 'esperar', 'timeout': 300, 'parametros': {'segundos': 1}},
}


def pedir(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo else None
    req = urllib.request.Request(URL + ruta, data=datos, method=metodo,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def memoria_mb(pid):
    with open(f'/proc/{pid}/status') as f:
        for linea in f:
            if linea.startswith('VmRSS:'):
                return int(linea.split()[1]) / 1024
    return 0.0


def medir(modo, n):
    env = dict(os.environ, N_WORKERS=str(n))
    servidor = subprocess.Popen([sys.executable, 'main.py'], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                pedir('GET', '/')
                break
            except OSError:
                time.sleep(0.1)
        mem_antes = memoria_mb(servidor.pid)

        t_envio = time.perf_counter()
        with ThreadPoolExecutor(32) as hilos:
            list(hilos.map(lambda _: pedir('POST', '/tareas', TAREA[modo]), range(n)))
        envio = time.perf_counter() - t_envio

        t0 = time.perf_counter()
        stats = pedir('GET', '/estadisticas')
        latencia = (time.perf_counter() - t0) * 1000
        mem_pico = memoria_mb(servidor.pid)

        while stats['por_estado']['completada'] + stats['por_estado']['fallida'] < n:
            time.sleep(0.2)
            stats = pedir('GET', '/estadisticas')
            mem_pico = max(mem_pico, memoria_mb(servidor.pid))

        tareas = pedir('GET', '/tareas')
        total = max(t['finalizada'] for t in tareas) - min(t['creada'] for t in tareas)
        ejec = [t['finalizada'] - t['iniciada'] for t in tareas if t['iniciada']]
        print(f'{modo:>3} N={n:>6} | envío {envio:6.2f} s | total {total:7.2f} s | '
              f'ejecución prom {sum(ejec) / len(ejec):6.2f} s, peor {max(ejec):6.2f} s | '
              f'GET stats {latencia:7.1f} ms | memoria {mem_antes:5.0f} → {mem_pico:5.0f} MB '
              f'| fallidas {stats["por_estado"]["fallida"]}', flush=True)
    finally:
        servidor.terminate()
        servidor.wait()


if __name__ == '__main__':
    for n in sys.argv[2:]:
        medir(sys.argv[1], int(n))

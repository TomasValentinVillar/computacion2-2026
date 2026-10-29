#!/usr/bin/env python3
"""Medición 1: 20 descargas secuenciales contra 20 concurrentes.

Usa una URL que siempre tarda ~1 s (httpbin.org/delay/1), así el resultado no
depende de qué tan rápido responde cada sitio. Mide con los timestamps que
guarda el propio sistema (creada / finalizada).

- secuencial:  20 tareas de 1 URL cada una (con N_WORKERS=1 se procesan de a una)
- concurrente: 1 tarea con las 20 URLs (adentro se bajan con asyncio.gather)

Uso (con el servidor levantado):
    python3 medir_io.py [secuencial|concurrente] [cantidad]
"""
import json
import sys
import time
import urllib.request

URL = 'http://localhost:8000'
DESCARGA = 'https://httpbin.org/delay/1'
MODO = sys.argv[1] if len(sys.argv) > 1 else 'concurrente'
CANTIDAD = int(sys.argv[2]) if len(sys.argv) > 2 else 20


def pedir(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo else None
    req = urllib.request.Request(URL + ruta, data=datos, method=metodo,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def crear(urls):
    return pedir('POST', '/tareas', {'tipo': 'descargar', 'timeout': 300,
                                     'parametros': {'urls': urls}})['id']


def main():
    if MODO == 'secuencial':
        ids = [crear([DESCARGA]) for _ in range(CANTIDAD)]
    else:
        ids = [crear([DESCARGA] * CANTIDAD)]

    finales = ('completada', 'fallida', 'cancelada')
    while True:
        tareas = [pedir('GET', f'/tareas/{i}') for i in ids]
        if all(t['estado'] in finales for t in tareas):
            break
        time.sleep(0.2)

    total = max(t['finalizada'] for t in tareas) - min(t['creada'] for t in tareas)
    descargas = [r for t in tareas for r in (t['resultado'] or [])]
    ok = sum(1 for r in descargas if r.get('codigo') == 200)
    print(f'{MODO}: {CANTIDAD} descargas de {DESCARGA}')
    print(f'  tiempo total:         {total:6.2f} s')
    print(f'  descargas con 200:    {ok}/{CANTIDAD}')
    if descargas:
        tiempos = [r['segundos'] for r in descargas]
        print(f'  cada una: min {min(tiempos):.2f} s, máx {max(tiempos):.2f} s')
    for r in descargas:
        if r.get('codigo') != 200:
            print(f"  sin 200: {r.get('codigo') or r.get('error')} en {r['segundos']} s")


if __name__ == '__main__':
    main()

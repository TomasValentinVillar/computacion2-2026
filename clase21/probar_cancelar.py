import json
import time
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:8000'
FINALES = {'completada', 'cancelada', 'error'}


def pedir(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def crear(tipo):
    return pedir('POST', '/tareas', {'tipo': tipo})[1]['id']


def estado(tid):
    return pedir('GET', f'/tareas/{tid}')[1]['estado']


def hasta_terminar(tid):
    t0 = time.perf_counter()
    while estado(tid) not in FINALES:
        time.sleep(0.05)
    return time.perf_counter() - t0


print('=== A: referencia, un hashear solo ===')
tid = crear('hashear')
print(f'  tardó {hasta_terminar(tid):.2f}s en completarse')

print('\n=== B: cancelar un esperar (3s) en ejecución ===')
tid = crear('esperar')
time.sleep(0.5)
print(f'  antes del DELETE: {estado(tid)}')
t0 = time.perf_counter()
codigo, cuerpo = pedir('DELETE', f'/tareas/{tid}')
print(f'  DELETE -> {codigo}, estado {cuerpo["estado"]}')
time.sleep(0.1)
print(f'  después: {estado(tid)}  (a los {0.5 + time.perf_counter() - t0:.1f}s, no a los 3)')

print('\n=== C: cancelar una pendiente ===')
bloqueadores = [crear('esperar') for _ in range(4)]   # ocupan los 4 workers
time.sleep(0.1)
tid = crear('esperar')
print(f'  la quinta está: {estado(tid)}')
codigo, cuerpo = pedir('DELETE', f'/tareas/{tid}')
print(f'  DELETE -> {codigo}, estado {cuerpo["estado"]}')
for b in bloqueadores:                                # liberar los workers
    pedir('DELETE', f'/tareas/{b}')
time.sleep(0.2)
print(f'  después de liberar los workers: {estado(tid)}  (el worker la salteó)')

print('\n=== D: casos que no se pueden cancelar ===')
codigo, cuerpo = pedir('DELETE', '/tareas/1')
print(f'  DELETE de una completada -> {codigo}: {cuerpo["detail"]}')
codigo, cuerpo = pedir('DELETE', '/tareas/9999')
print(f'  DELETE de una inexistente -> {codigo}: {cuerpo["detail"]}')

print('\n=== E: cancelar un hashear... ¿frena el cálculo? ===')
cancelados = [crear('hashear') for _ in range(2)]     # ocupan los 2 procesos del pool
time.sleep(0.2)
for c in cancelados:
    codigo, cuerpo = pedir('DELETE', f'/tareas/{c}')
    print(f'  DELETE hashear {c} -> {codigo}, estado {cuerpo["estado"]}')
tid = crear('hashear')
print(f'  un hashear nuevo, después de cancelar esos dos, tardó {hasta_terminar(tid):.2f}s')

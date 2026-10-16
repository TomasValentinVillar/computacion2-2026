from collections import deque
import time
import sys

def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f' [{nombre}] paso {i}/{pasos}')
        yield

def tarea_lenta(nombre, veces, espera=0.15):
    for i in range(1, veces + 1):
        print(f'  [{nombre}] {i}/{veces} (t={time.monotonic() - T0:.2f}s)')
        yield from dormir(espera)
    print(f' [{nombre}] terminada')

def scheduler(tareas):
    pendientes = deque(tareas)
    n = 0
    while pendientes:
        t = pendientes.popleft()
        try:
            next(t)
            n += 1
            print(f'contador de yield: {n}')
            pendientes.append(t)
        except StopIteration:
            pass

def dormir(segundos):
    yield time.monotonic() + segundos

def scheduler_con_tiempo(tareas):
    pendientes = deque((0.0, t) for t in tareas)
    while pendientes:
        despertar, t = pendientes.popleft()
        if time.monotonic() < despertar:
            pendientes.append((despertar, t))
            continue
        try:
            cuando = next(t)
            pendientes.append((cuando or 0.0, t))
        except StopIteration:
            pass


if __name__ == '__main__':
    T0 = time.monotonic()
    if '--tiempo' in sys.argv:
        print('=== Tres tareas que esperan, intercaladas en un hilo ===')
        t0 = time.monotonic()
        scheduler_con_tiempo([
            tarea_lenta('A', 3),
            tarea_lenta('B', 2),
            tarea_lenta('C', 4),
        ])
        print(f'\nTotal: {time.monotonic() - t0:.2f}s')
        print('Las esperas se solapan: no es la suma de todas.')
    else:
        print('=== Tres tareas intercaladas en UN solo hilo ===')
        v = scheduler([tarea('A', 3), tarea('B', 2), tarea('C', 4)])
        print(f'\nEl scheduler hizo {v} reanudaciones.')
        print('Sin threads, sin procesos: solo generadores y una cola.')

#!/usr/bin/env python3
"""Cálculo paralelo usando Value compartido."""
from multiprocessing import Process, Value, Array
import math
import time

def calcular_rango(resultado, total, inicio, fin):
    for i in range(inicio, fin):
        valor = math.sin(i * 0.01)
        resultado[i] = valor
        total.value += valor   # ← acá vas a tener la race condition

# Array compartido de 1000 enteros
TAMAÑO = 1000000
resultado = Array('d', TAMAÑO)
total = Value('d', 0.0)

# Dividir en 4 procesos
NUM_PROCESOS = 4
chunk = TAMAÑO // NUM_PROCESOS

inicio = time.time()

procesos = []
for i in range(NUM_PROCESOS):
    ini = i * chunk
    fin = (i + 1) * chunk if i < NUM_PROCESOS - 1 else TAMAÑO
    p = Process(target=calcular_rango, args=(resultado,total, ini, fin))
    p.start()
    procesos.append(p)

for p in procesos:
    p.join()

duracion = time.time() - inicio

# Verificar
print(f"Cálculo completado en {duracion:.4f}s")

for i in range(21):
    print(f"resultado[{i}] = {resultado[i]}")

# Verificar que todos son correctos
errores = sum(1 for i in range(TAMAÑO) if resultado[i] != math.sin(i * 0.01))
print(f"Errores: {errores}")

print(f"\nSuma paralela (con race condition): {total.value}")
suma_serial = sum(math.sin(i * 0.01) for i in range(TAMAÑO))
print(f"Suma serial (correcta):              {suma_serial}")
print(f"Diferencia (perdida):                {suma_serial - total.value}")
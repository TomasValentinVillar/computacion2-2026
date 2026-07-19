#!/usr/bin/env python3
"""Banco con log de transferencias."""
from multiprocessing import Process, Array
import random
import os

NUM_CUENTAS = 5
SALDO_INICIAL = 1000
NUM_PROCESOS = 3
TRANSFERENCIAS_POR_PROCESO = 100
LOG_FILE = "/tmp/banco_log.csv"

def mostrar_saldos(cuentas, etiqueta):
    saldos = [cuentas[i] for i in range(NUM_CUENTAS)]
    total = sum(saldos)
    print(f"[{etiqueta}] Saldos: {saldos} | Total: {total}")

def cajero(cuentas, cajero_id, num_transferencias):
    for _ in range(num_transferencias):
        origen = random.randint(0, NUM_CUENTAS - 1)
        destino = random.randint(0, NUM_CUENTAS - 1)
        while destino == origen:
            destino = random.randint(0, NUM_CUENTAS - 1)
        
        monto = random.randint(1, 50)
        
        if cuentas[origen] >= monto:
            cuentas[origen] -= monto
            cuentas[destino] += monto
            
            # COMPLETAR: escribir la transferencia al log
            # Formato sugerido: "cajero_id,origen,destino,monto\n"
            with open(LOG_FILE, "a") as f:
                f.write(f"{cajero_id},{origen},{destino},{monto}\n")
    
    print(f"[Cajero {cajero_id}] Completó {num_transferencias} transferencias")

# Limpiar log anterior si existe
if os.path.exists(LOG_FILE):
    os.unlink(LOG_FILE)

# Crear array compartido
cuentas = Array('i', [SALDO_INICIAL] * NUM_CUENTAS)

print(f"=== Banco con {NUM_CUENTAS} cuentas ===")
print(f"=== Saldo total esperado: {NUM_CUENTAS * SALDO_INICIAL} ===\n")

mostrar_saldos(cuentas, "INICIO")

procesos = []
for i in range(NUM_PROCESOS):
    p = Process(target=cajero, args=(cuentas, i, TRANSFERENCIAS_POR_PROCESO))
    p.start()
    procesos.append(p)

for p in procesos:
    p.join()

mostrar_saldos(cuentas, "FINAL")

# Verificar integridad de saldos
total_final = sum(cuentas[i] for i in range(NUM_CUENTAS))
total_esperado = NUM_CUENTAS * SALDO_INICIAL
diferencia = total_final - total_esperado
if diferencia == 0:
    print(f"\nSaldos OK (pero fue suerte)")
else:
    print(f"\n¡ERROR! Diferencia: ${diferencia}")

# Analizar el log
print(f"\n=== Análisis del log ===")
with open(LOG_FILE, "r") as f:
    lineas = f.readlines()

print(f"Total de transferencias logueadas: {len(lineas)}")
print(f"\nPrimeras 5 entradas:")
for linea in lineas[:5]:
    print(f"  {linea.strip()}")
print(f"\nÚltimas 5 entradas:")
for linea in lineas[-5:]:
    print(f"  {linea.strip()}")

#!/usr/bin/env python3
"""Varios hijos escriben en regiones separadas del mmap."""
import mmap
import os
import struct

NUM_HIJOS = 4
TAMAÑO_POR_HIJO = 25
TAMAÑO_TOTAL = NUM_HIJOS * TAMAÑO_POR_HIJO

mm = mmap.mmap(-1, TAMAÑO_TOTAL)

hijos = []
for i in range(NUM_HIJOS):
    pid = os.fork()
    if pid == 0:
        # Hijo: escribe en su región
        offset = i * TAMAÑO_POR_HIJO
        limite = offset + TAMAÑO_POR_HIJO
        num = 0
        for j in range(offset + 1, limite + 1):
            num = num + j 
        struct.pack_into('i', mm, offset, num)

        os._exit(0)
    else:
        hijos.append(pid)

# Padre espera a todos
for pid in hijos:
    os.waitpid(pid, 0)

# Leer resultados
print("=== Calculando Total ===")
total = 0
for i in range(NUM_HIJOS):
    offset = i * TAMAÑO_POR_HIJO
    num = struct.unpack_from('i', mm, offset)[0]
    print(f'num: {num}')
    total = total + num
print(f'Total: {total}')
mm.close()
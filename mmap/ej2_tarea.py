#!/usr/bin/env python3
"""Almacenar registros (id, nota, nombre) en mmap."""
import mmap
import struct
import os

ARCHIVO = "/tmp/registros.bin"
NUM_REGISTROS = 5
FORMATO = 'if20s'                           # int + float + 20 bytes string
TAMAÑO_REGISTRO = struct.calcsize(FORMATO)  # ¡que lo calcule struct!
TAMAÑO_TOTAL = NUM_REGISTROS * TAMAÑO_REGISTRO

print(f"Cada registro ocupa {TAMAÑO_REGISTRO} bytes")
print(f"Total del archivo: {TAMAÑO_TOTAL} bytes\n")

# Datos a guardar
registros = [
    (1, 8.5, b"Lionel Messi"),
    (2, 9.0, b"Diego Maradona"),
    (3, 7.5, b"Tomas Villar"),
    (4, 8.0, b"Sergio Aguero"),
    (5, 9.5, b"Angel Di Maria"),
]

# Paso 1: pre-asignar el archivo
with open(ARCHIVO, "wb") as f:
    f.write(b'\x00' * TAMAÑO_TOTAL)

# Paso 2: mapear y escribir los registros
with open(ARCHIVO, "r+b") as f:
    mm = mmap.mmap(f.fileno(), TAMAÑO_TOTAL)
    
    print("=== Escribiendo registros ===")
    for i, (id_, nota, nombre) in enumerate(registros):
        offset = i * 28
        struct.pack_into(FORMATO, mm, offset, id_, nota, nombre)
        print(f"  Reg {i}: id={id_}, nota={nota}, nombre={nombre.decode()}")
    
    # Paso 3: leer y mostrar todos los registros
    print("\n=== Leyendo registros ===")
    for i in range(NUM_REGISTROS):
        offset = i * 28
        id_, nota, nombre_raw = struct.unpack_from(FORMATO, mm, offset)
        nombre = nombre_raw.rstrip(b'\x00').decode()
        print(f"  Reg {i}: id={id_}, nota={nota}, nombre='{nombre}'")
    
    mm.close()

os.unlink(ARCHIVO)
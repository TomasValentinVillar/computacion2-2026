#!/usr/bin/env python3
"""Reemplazar palabra en archivo usando mmap."""
import mmap

RUTA = "/tmp/mmap_ej1.txt"
PALABRA_VIEJA = b"perro"   # cambiá por lo que quieras
PALABRA_NUEVA = b"gatos"   # mismo largo en bytes!

# Verificación previa: que tengan el mismo largo
assert len(PALABRA_VIEJA) == len(PALABRA_NUEVA), "Las palabras deben tener el mismo largo"

# Paso 1: crear el archivo con 5 líneas
with open(RUTA, "wb") as f:
     f.write(b"Linea 1: El perro ladra\n")
     f.write(b"Linea 2: El perro es mi amigo\n")
     f.write(b"Linea 3: No me gustan los perros\n")
     f.write(b"Linea 4: El perro es un animal\n")
     f.write(b"Linea 5: Los perros son leales\n")

# Paso 2: abrir el archivo en modo lectura+escritura binario y mapearlo
with open(RUTA, "r+b") as f:
    mm = mmap.mmap(f.fileno(), 0)
    
    # Paso 3: mostrar el contenido original
    print("=== ANTES ===")
    print(mm[:].decode())
    
    # Paso 4: buscar y reemplazar TODAS las ocurrencias en un loop
    cantidad = 0
    pos = mm.find(PALABRA_VIEJA, 0)   # buscar desde el inicio
    while pos != -1:
        mm[pos:pos+len(PALABRA_NUEVA)] = PALABRA_NUEVA
        cantidad += 1
        pos = mm.find(PALABRA_VIEJA, pos + 1)
    
    print(f"\nReemplacé {cantidad} ocurrencias")
    
    # Paso 5: mostrar el contenido modificado
    print("\n=== DESPUÉS ===")
    print(mm[:].decode())
    
    mm.close()

print(f"\nVerificá con: cat {RUTA}")
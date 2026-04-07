#!/usr/bin/env python3
import os
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser(description="Comparador de directorios")
parser.add_argument("dir1")
parser.add_argument("dir2")
parser.add_argument("--checksum", action="store_true")
parser.add_argument("--recursive", action="store_true")
args = parser.parse_args()

def hash_archivo(ruta):
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def timestamp_a_fecha(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

def obtener_archivos(directorio, recursivo):
    directorio = Path(directorio)
    if recursivo:
        return set(p.relative_to(directorio) for p in directorio.rglob("*") if p.is_file())
    else:
        return set(p.name for p in directorio.iterdir() if p.is_file())

dir1 = Path(args.dir1)
dir2 = Path(args.dir2)

print(f"Comparando {dir1} con {dir2}...")

archivos_dir1 = obtener_archivos(dir1, args.recursive)
archivos_dir2 = obtener_archivos(dir2, args.recursive)

solo_en_dir1 = archivos_dir1 - archivos_dir2
solo_en_dir2 = archivos_dir2 - archivos_dir1
en_ambos     = archivos_dir1 & archivos_dir2

if solo_en_dir1:
    print(f"\nSolo en {dir1}:")
    for nombre in sorted(solo_en_dir1):
        print(f"  {nombre}")

if solo_en_dir2:
    print(f"\nSolo en {dir2}:")
    for nombre in sorted(solo_en_dir2):
        print(f"  {nombre}")

modificados_tamanio = []
modificados_fecha = []
identicos = 0

for nombre in sorted(en_ambos):
    ruta1 = dir1 / nombre
    ruta2 = dir2 / nombre

    info1 = ruta1.stat()
    info2 = ruta2.stat()

    if args.checksum:
        if hash_archivo(ruta1) != hash_archivo(ruta2):
            modificados_tamanio.append((nombre, info1.st_size, info2.st_size))
        else:
            identicos += 1
    else:
        if info1.st_size != info2.st_size:
            modificados_tamanio.append((nombre, info1.st_size, info2.st_size))
        elif info1.st_mtime != info2.st_mtime:
            modificados_fecha.append((nombre, info1.st_mtime, info2.st_mtime))
        else:
            identicos += 1

if modificados_tamanio:
    if args.checksum:
        print("\nModificados (contenido diferente):")
    else:
        print("\nModificados (tamaño diferente):")
    for nombre, t1, t2 in modificados_tamanio:
        print(f"  {nombre} ({t1} -> {t2} bytes)")

if modificados_fecha:
    print("\nModificados (fecha diferente):")
    for nombre, f1, f2 in modificados_fecha:
        print(f"  {nombre} ({timestamp_a_fecha(f1)} -> {timestamp_a_fecha(f2)})")

print(f"\nIdénticos: {identicos} archivos")
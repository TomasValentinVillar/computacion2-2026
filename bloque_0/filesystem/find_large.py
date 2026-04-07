#!/usr/bin/env python3
import os
import stat
import sys
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description="Buscador de archivos grandes")
parser.add_argument("directorio")
parser.add_argument("--min-size", required=True)
parser.add_argument("--type", choices=["f", "d"], dest="tipo")
parser.add_argument("--top", type=int)
args = parser.parse_args()

def parsear_tamanio(texto):
    unidades = {"K": 1024, "M": 1024**2, "G": 1024**3}
    ultimo = texto[-1].upper()
    if ultimo in unidades:
        numero = float(texto[:-1])
        return int(numero * unidades[ultimo])
    else:
        return int(texto)
    
def formatear_tamanio(bytes):
    if bytes >= 1024**3:
        return f"{bytes / 1024**3:.1f} GB"
    elif bytes >= 1024**2:
        return f"{bytes / 1024**2:.1f} MB"
    elif bytes >= 1024:
        return f"{bytes / 1024:.1f} KB"
    else:
        return f"{bytes} bytes"

min_bytes = parsear_tamanio(args.min_size)
directorio = Path(args.directorio)
encontrados = []

for ruta in directorio.rglob("*"):
    try:
        info = ruta.lstat()
        modo = info.st_mode

        # filtro por tipo
        if args.tipo == "f" and not stat.S_ISREG(modo):
            continue
        if args.tipo == "d" and not stat.S_ISDIR(modo):
            continue

        # filtro por tamaño
        if info.st_size >= min_bytes:
            encontrados.append((ruta, info.st_size))

    except PermissionError:
        continue

encontrados.sort(key=lambda x: x[1], reverse=True)

if args.top:
    print(f"Los {args.top} archivos más grandes:")
    encontrados = encontrados[:args.top]
    for i, (ruta, tamanio) in enumerate(encontrados, 1):
        print(f"  {i}. {ruta} ({formatear_tamanio(tamanio)})")
else:
    for ruta, tamanio in encontrados:
        print(f"{ruta} ({formatear_tamanio(tamanio)})")

total_bytes = sum(t for _, t in encontrados)
print(f"\nTotal: {len(encontrados)} archivos, {formatear_tamanio(total_bytes)}")

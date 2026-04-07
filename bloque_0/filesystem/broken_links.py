#!/usr/bin/env python3
import os
import sys
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description="Detector de enlaces rotos")
parser.add_argument("directorio")
parser.add_argument("--delete", action="store_true")
parser.add_argument("--quiet", action="store_true")
args = parser.parse_args()

directorio = Path(args.directorio)
rotos = []

if not args.quiet:
    print(f"Buscando enlaces simbólicos rotos en {directorio}...")

for ruta in directorio.rglob("*"):
    if ruta.is_symlink() and not ruta.exists():
        destino = os.readlink(ruta)
        rotos.append((ruta, destino))

if args.quiet:
    print(len(rotos))
else:
    if rotos:
        print("Enlaces rotos encontrados:")
        for ruta, destino in rotos:
            print(f"  {ruta} -> {destino} (no existe)")
    else:
        print("No se encontraron enlaces rotos")
    print(f"Total: {len(rotos)} enlaces rotos")

if args.delete and rotos:
    print()
    for ruta, destino in rotos:
        respuesta = input(f"¿Borrar {ruta}? [s/N]: ")
        if respuesta.lower() == "s":
            ruta.unlink()
            print(f"  Borrado.")
        else:
            print(f"  Omitido.")

#!/usr/bin/env python3
import argparse
import os
 
parser = argparse.ArgumentParser(description="Listador de archivos mejorado.")
parser.add_argument("directorio", nargs="?", default=".", help="Directorio a listar (default: directorio actual)")
parser.add_argument("-a", "--all", action="store_true", help="Incluir archivos ocultos")
parser.add_argument("--extension", help="Filtrar por extensión (ej: .py)")
 
args = parser.parse_args()
 
# Obtener la lista de archivos
archivos = os.listdir(args.directorio)
 
# Ordenar alfabéticamente
archivos = sorted(archivos)
 
for nombre in archivos:
 
    # Si no tiene --all, saltear los que empiezan con punto
    if not args.all and nombre.startswith("."):
        continue
 
    # Si tiene --extension, saltear los que no coincidan
    if args.extension and not nombre.endswith(args.extension):
        continue
 
    # Armar la ruta completa para saber si es directorio
    ruta_completa = os.path.join(args.directorio, nombre)
 
    # Mostrar con / al final si es directorio
    if os.path.isdir(ruta_completa):
        print(nombre + "/")
    else:
        print(nombre)
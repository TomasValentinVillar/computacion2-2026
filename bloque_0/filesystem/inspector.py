#!/usr/bin/env python3
import os
import stat
import pwd
import grp
import sys
from pathlib import Path
from datetime import datetime

ruta = Path(sys.argv[1])
info = os.lstat(ruta)  # lstat en vez de stat para no seguir symlinks

modo = info.st_mode

if stat.S_ISREG(modo):
    tipo = "archivo regular"
elif stat.S_ISDIR(modo):
    tipo = "directorio"
elif stat.S_ISLNK(modo):
    destino = os.readlink(ruta)
    tipo = f"enlace simbólico -> {destino}"
elif stat.S_ISCHR(modo):
    tipo = "dispositivo de caracteres"
elif stat.S_ISBLK(modo):
    tipo = "dispositivo de bloques"
else:
    tipo = "otro"

permisos_str = stat.filemode(modo)[1:]  # saca el primer caracter (tipo)
permisos_oct = oct(stat.S_IMODE(modo))[2:]  # saca el "0o" del principio

usuario = pwd.getpwuid(info.st_uid).pw_name
grupo = grp.getgrgid(info.st_gid).gr_name

tamanio_bytes = info.st_size
tamanio_kb = tamanio_bytes / 1024

def timestamp_a_fecha(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

fecha_modificacion = timestamp_a_fecha(info.st_mtime)
fecha_acceso = timestamp_a_fecha(info.st_atime)
fecha_cambio = timestamp_a_fecha(info.st_ctime)

print(f"Archivo: {ruta}")
print(f"Tipo: {tipo}")
print(f"Tamaño: {tamanio_bytes} bytes ({tamanio_kb:.2f} KB)")
print(f"Permisos: {permisos_str} ({permisos_oct})")
print(f"Propietario: {usuario} (uid: {info.st_uid})")
print(f"Grupo: {grupo} (gid: {info.st_gid})")
print(f"Inodo: {info.st_ino}")
print(f"Enlaces duros: {info.st_nlink}")
print(f"Última modificación: {fecha_modificacion}")
print(f"Último acceso: {fecha_acceso}")
print(f"Último cambio de metadatos: {fecha_cambio}")

if stat.S_ISDIR(modo):
    elementos = len(os.listdir(ruta))
    print(f"Contenido: {elementos} elementos")
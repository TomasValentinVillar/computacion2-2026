#!/usr/bin/env python3
import argparse
import secrets
import string

parser = argparse.ArgumentParser(description="Generador de contraseñas seguras.")
parser.add_argument("-n", "--length", type=int, default=12, help="Longitud de la contraseña (default: 12)")
parser.add_argument("--no-symbols", action="store_true", help="Excluir símbolos especiales")
parser.add_argument("--no-numbers", action="store_true", help="Excluir números")
parser.add_argument("--count", type=int, default=1, help="Cuántas contraseñas generar (default: 1)")

args = parser.parse_args()

# Definir los caracteres disponibles
LETRAS = string.ascii_letters   # a-z y A-Z
NUMEROS = string.digits         # 0-9
SIMBOLOS = "!@#$%&"

# Armar el pool según las opciones
pool = LETRAS

if not args.no_numbers:
    pool += NUMEROS

if not args.no_symbols:
    pool += SIMBOLOS

# Generar las contraseñas
for i in range(args.count):
    contrasena = "".join(secrets.choice(pool) for _ in range(args.length))
    print(contrasena)
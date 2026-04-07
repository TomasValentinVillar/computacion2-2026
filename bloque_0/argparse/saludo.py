import sys

if len(sys.argv) < 2:
    print("Uso: saludo.py <nombre>")
    sys.exit(1)

nombre_completo = " ".join(sys.argv[1: ]) #que hace esta liena
print(f"Hola, {nombre_completo}!")
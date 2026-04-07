#!/usr/bin/env python3
import argparse
import sys

parser = argparse.ArgumentParser(description="Busca patrones en archivos de texto.")
parser.add_argument("patron", help="Patrón a buscar")
parser.add_argument("archivos", nargs="*", help="Archivos donde buscar (default: stdin)")
parser.add_argument("-i", "--ignore-case", action="store_true", help="Ignorar mayúsculas/minúsculas")
parser.add_argument("-n", "--line-number", action="store_true", help="Mostrar número de línea")
parser.add_argument("-c", "--count", action="store_true", help="Mostrar solo conteo de coincidencias")
parser.add_argument("-v", "--invert", action="store_true", help="Mostrar líneas que NO coinciden")

args = parser.parse_args()


def buscar_en_archivo(fuente, nombre_archivo, mostrar_nombre):
    """Busca el patrón en una fuente (archivo o stdin) y muestra los resultados."""
    
    patron = args.patron.lower() if args.ignore_case else args.patron
    coincidencias = 0

    for numero, linea in enumerate(fuente, start=1):
        linea = linea.rstrip("\n")

        # Preparar la línea para comparar
        linea_comparar = linea.lower() if args.ignore_case else linea

        # Ver si hay coincidencia
        hay_coincidencia = patron in linea_comparar

        # Si --invert, invertir el resultado
        if args.invert:
            hay_coincidencia = not hay_coincidencia

        if not hay_coincidencia:
            continue

        coincidencias += 1

        # Si --count, no imprimir líneas todavía
        if args.count:
            continue

        # Armar el prefijo de la línea
        partes = []

        if mostrar_nombre:
            partes.append(nombre_archivo)

        if args.line_number or mostrar_nombre:
            partes.append(str(numero))

        if partes:
            print(":".join(partes) + ": " + linea)
        else:
            print(linea)

    return coincidencias


def main():
    multiples_archivos = len(args.archivos) > 1
    total = 0

    # Si no hay archivos, leer de stdin
    if not args.archivos:
        if sys.stdin.isatty():
            print("Error: especificá un archivo o usá un pipe", file=sys.stderr)
            sys.exit(1)
        coincidencias = buscar_en_archivo(sys.stdin, "stdin", mostrar_nombre=False)
        if args.count:
            print(f"Total: {coincidencias} coincidencias")
        return

    # Procesar cada archivo
    for nombre_archivo in args.archivos:
        try:
            with open(nombre_archivo, "r") as f:
                coincidencias = buscar_en_archivo(f, nombre_archivo, mostrar_nombre=multiples_archivos)
                total += coincidencias
                if args.count:
                    print(f"{nombre_archivo}: {coincidencias} coincidencias")
        except FileNotFoundError:
            print(f"Error: No se puede leer '{nombre_archivo}'", file=sys.stderr)
        except PermissionError:
            print(f"Error: No se puede leer '{nombre_archivo}'", file=sys.stderr)

    if args.count and multiples_archivos:
        print(f"Total: {total} coincidencias")


if __name__ == "__main__":
    main()
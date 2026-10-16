#!/usr/bin/env python3
"""Ejercicio 4.1: contador compartido, corrutinas vs threads.

Uso:
    python3 contador.py
"""
import asyncio
import sys
import threading

contador = 0


def identidad(x):
    return x


# --- corrutinas ---

async def sumar(vueltas):
    global contador
    for _ in range(vueltas):
        contador += 1


async def con_corrutinas(tareas, vueltas):
    global contador
    contador = 0
    await asyncio.gather(*(sumar(vueltas) for _ in range(tareas)))
    return contador


# --- threads ---

def sumar_thread(vueltas):
    global contador
    for _ in range(vueltas):
        contador += 1


def sumar_thread_con_llamada(vueltas):
    global contador
    for _ in range(vueltas):
        valor = contador                  # leo
        valor = identidad(valor) + 1      # una llamada entre leer y escribir
        contador = valor                  # escribo


def con_threads(funcion, cantidad, vueltas):
    global contador
    contador = 0
    hilos = [threading.Thread(target=funcion, args=(vueltas,))
             for _ in range(cantidad)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return contador


def mostrar(etiqueta, esperado, obtenido):
    estado = 'OK' if obtenido == esperado else f'PERDIÓ {esperado - obtenido}'
    print(f'  {etiqueta:38} esperado {esperado:>9}  '
          f'obtenido {obtenido:>9}  {estado}')


def main():
    print(f'Python {sys.version.split()[0]}\n')

    mostrar('corrutinas: 1000 tareas x 1', 1000,
            asyncio.run(con_corrutinas(1000, 1)))
    mostrar('corrutinas: 1000 tareas x 1000', 1_000_000,
            asyncio.run(con_corrutinas(1000, 1000)))

    sys.setswitchinterval(1e-6)       # que el intérprete cambie de thread seguido

    mostrar('threads: 1000 x 1', 1000,
            con_threads(sumar_thread, 1000, 1))
    mostrar('threads: 100 x 10000', 1_000_000,
            con_threads(sumar_thread, 100, 10_000))
    mostrar('threads: 100 x 10000, con llamada', 1_000_000,
            con_threads(sumar_thread_con_llamada, 100, 10_000))


if __name__ == '__main__':
    main()

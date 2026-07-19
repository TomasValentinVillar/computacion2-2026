#!/usr/bin/env python3
"""
Monitor que ejecuta comandos en paralelo y reporta resultados.
"""
import os
import sys
import time

def ejecutar_paralelo(comandos):
    """
    Ejecuta una lista de comandos en paralelo.
    Retorna dict con {pid: (comando, codigo_salida)}
    """
    procesos = {}  # pid -> comando

    # Crear un hijo por cada comando
    for cmd in comandos:
        pid = os.fork()

        if pid == 0:
            # Hijo: ejecutar comando
            partes = cmd.split()
            try:
                os.execvp(partes[0], partes)
            except OSError as e:
                print(f"Error ejecutando '{cmd}': {e}", file=sys.stderr)
                os._exit(127)
        else:
            # Padre: registrar el hijo
            procesos[pid] = cmd
            print(f"[{pid}] Iniciado: {cmd}")

    # Esperar a todos los hijos
    resultados = {}
    while procesos:
        pid, status = os.wait()
        cmd = procesos.pop(pid)
        codigo = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
        resultados[pid] = (cmd, codigo)
        print(f"[{pid}] Terminado: {cmd} (código {codigo})")

    return resultados

if __name__ == "__main__":
    comandos = [
        "sleep 2",
        "ls /tmp",
        "echo hola mundo",
        "sleep 1",
    ]

    print("=== Ejecutando comandos en paralelo ===")
    inicio = time.time()
    resultados = ejecutar_paralelo(comandos)
    duracion = time.time() - inicio

    print(f"\n=== Resumen (duración total: {duracion:.1f}s) ===")
    exitos = sum(1 for _, (_, codigo) in resultados.items() if codigo == 0)
    print(f"Exitosos: {exitos}/{len(resultados)}")
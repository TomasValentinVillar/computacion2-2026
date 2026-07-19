import multiprocessing
import time
import random
import sys
import os

def worker(cmd):
     # Hijo: ejecutar comando
        partes = cmd.split()
        try:
            os.execvp(partes[0], partes)
        except OSError as e:
            print(f"Error ejecutando '{cmd}': {e}", file=sys.stderr)
            sys.exit(127) 

if __name__ == "__main__":
    procesos = []
    comandos = [
        "sleep 2",
        "ls /tmp",
        "echo hola mundo",
        "sleep 1",
    ]
    inicio = time.time()
    cmds = {}
    for cmd in comandos:
        p = multiprocessing.Process(target=worker, args=(cmd,))
        p.start()
        procesos.append(p)
        cmds[p] = cmd
    resultados = {}

    for p in procesos:
        pid = p.pid
        p.join()
        cmd = cmds.pop(p)
        resultados[pid] = (cmd, p.exitcode)
        print(f"[{pid}] Terminado: {cmd} (código {p.exitcode})")
    duracion = time.time() - inicio

    print(f"\n=== Resumen (duración total: {duracion:.1f}s) ===")
    exitos = sum(1 for _, (_, codigo) in resultados.items() if codigo == 0)
    print(f"Exitosos: {exitos}/{len(resultados)}")
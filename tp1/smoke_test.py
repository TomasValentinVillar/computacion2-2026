#!/usr/bin/env python3
"""
smoke_test.py - Valida que la infraestructura del contenedor esté bien configurada.

Comprueba dos cosas antes de construir el monitor encima:
  1. pid: host        -> ¿vemos los procesos del HOST o solo los del contenedor?
  2. CAP_SYS_PTRACE   -> ¿podemos leer las "tripas" (FDs) de un proceso ajeno?

Si las dos pasan, la base está firme y se puede seguir.
"""

import os

# --- Umbral: con pid:host esperamos CIENTOS de procesos.
# Sin pid:host, un contenedor recien arrancado tiene un puñado (~3).
# 50 separa con claridad los dos mundos.
UMBRAL_PROCESOS = 50


def contar_pids():
    """Cuenta cuantas entradas de /proc son PIDs (carpetas cuyo nombre es un numero)."""
    entradas = os.listdir("/proc")
    # /proc tiene numeros (PIDs) y nombres (cpuinfo, meminfo, self, ...).
    # isdigit() nos deja SOLO los que son puramente numericos.
    pids = [nombre for nombre in entradas if nombre.isdigit()]
    return pids


def puedo_leer_fds(pid):
    """
    Intenta leer los symlinks de /proc/<pid>/fd/.
    Devuelve True si pudo, False si el kernel lo negó por falta de permisos.
    """
    ruta_fd = f"/proc/{pid}/fd"
    try:
        fds = os.listdir(ruta_fd)          # listar los numeros de FD (esto suele andar)
        if not fds:
            return None                    # el proceso no tiene FDs para probar
        # readlink es lo que REALMENTE necesita CAP_SYS_PTRACE:
        # seguir el symlink para ver a donde apunta el FD.
        os.readlink(os.path.join(ruta_fd, fds[0]))
        return True
    except PermissionError:
        # El kernel nos dijo "no": no tenemos la capability para espiar este proceso.
        return False
    except (FileNotFoundError, ProcessLookupError):
        # El proceso murio entre que lo elegimos y lo leimos. No es un fallo de infra.
        return None


def main():
    print("=== SMOKE TEST DE INFRAESTRUCTURA ===\n")

    # --- Chequeo 1: visibilidad (pid: host) ---
    pids = contar_pids()
    cantidad = len(pids)
    print(f"[1] Procesos visibles en /proc: {cantidad}")
    if cantidad > UMBRAL_PROCESOS:
        print(f"    OK -> vemos el HOST (pid: host funciona)\n")
        pid_host_ok = True
    else:
        print(f"    FALLO -> solo {cantidad} procesos. ¿Falta 'pid: host'?\n")
        pid_host_ok = False

    # --- Chequeo 2: acceso (CAP_SYS_PTRACE) ---
    # Buscamos un PID ajeno (distinto al nuestro) para probar de verdad.
    mi_pid = str(os.getpid())
    ptrace_ok = False
    for pid in pids:
        if pid == mi_pid:
            continue                       # leer los propios FDs no prueba nada
        resultado = puedo_leer_fds(pid)
        if resultado is True:
            print(f"[2] Lei los FDs del PID {pid} (ajeno)")
            print(f"    OK -> CAP_SYS_PTRACE funciona\n")
            ptrace_ok = True
            break
        elif resultado is False:
            print(f"[2] No pude leer los FDs del PID {pid} (Permission denied)")
            print(f"    continuo buscando otro PID...\n")
        # si es None, probamos con el siguiente

    # --- Veredicto ---
    print("=== VEREDICTO ===")
    if pid_host_ok and ptrace_ok:
        print("Infra OK. Se puede construir el monitor encima.")
    else:
        print("Infra INCOMPLETA. Revisar docker-compose.yml antes de seguir.")


if __name__ == "__main__":
    main()
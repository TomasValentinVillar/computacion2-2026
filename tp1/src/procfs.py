"""
procfs.py - Helpers compartidos para parsear /proc.

Estas funciones las usan varios analizadores (resumen, memoria, threads, etc.),
por eso viven acá y no dentro de un analizador puntual.
"""

import os


def parsear_stat(pid):
    """Parsea /proc/<pid>/stat. Devuelve dict con pid, comm, estado, ppid, utime, stime.
    Ojo: el campo comm (nombre) va entre paréntesis y puede tener espacios/paréntesis,
    por eso se corta la línea en 3 con rfind(')') en vez de split() directo."""
    with open(f"/proc/{pid}/stat") as f:
        linea = f.read()
    pid = linea[:linea.find('(')].strip()
    nombre = linea[linea.find('(')+1 : linea.rfind(')')]
    resto = linea[linea.rfind(')')+1:].split()
    estado = resto[0]
    ppid = resto[1]
    utime = resto[11]
    stime = resto[12]
    return {"pid": pid, "comm": nombre, "estado": estado, "ppid": ppid,
            "utime": utime, "stime": stime}


def parsear_status(pid):
    """Parsea /proc/<pid>/status. Devuelve dict clave->valor de todos los campos."""
    datos = {}
    with open(f"/proc/{pid}/status") as f:
        for linea in f:
            partes = linea.split(":", 1)
            clave = partes[0].strip()
            valor = partes[1].strip()
            datos[clave] = valor
    return datos


def leer_jiffies_sistema():
    """Lee la línea 'cpu' de /proc/stat y devuelve el total de jiffies del sistema."""
    with open("/proc/stat") as f:
        linea = f.readline()
    partes = linea.split()
    numeros = partes[1:]              # saltea la etiqueta 'cpu'
    total = sum(int(x) for x in numeros)
    return total


def calcular_cpu(pid, jiffies_ant_proc, jiffies_ant_sist, jiffies_sist_ahora):
    """Calcula el CPU% de un proceso con el delta de jiffies entre dos lecturas.
    Devuelve (cpu, jiffies_proc_ahora). Primera aparición del pid => 0.0."""
    d = parsear_stat(pid)
    jiffies_proc_ahora = int(d["utime"]) + int(d["stime"])

    if pid not in jiffies_ant_proc:
        cpu = 0.0
    else:
        delta_proc = jiffies_proc_ahora - jiffies_ant_proc[pid]
        delta_sist = jiffies_sist_ahora - jiffies_ant_sist
        if delta_sist == 0:
            cpu = 0.0
        else:
            cpu = (delta_proc / delta_sist) * 100

    return cpu, jiffies_proc_ahora
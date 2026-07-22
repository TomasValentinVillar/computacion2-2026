import os, time
from multiprocessing import Process, Manager

def parsear_stat(pid):
    with open(f"/proc/{pid}/stat") as f:
        linea = f.read()
    pid = linea[:linea.find('(')].strip()
    nombre = linea[linea.find('(')+1 : linea.rfind(')')]
    resto = linea[linea.rfind(')')+1:].split()
    estado = resto[0]
    ppid = resto[1]
    utime = resto[11]
    stime = resto[12]
    return {"pid": pid, "comm": nombre, "estado": estado, "ppid": ppid, "utime": utime, "stime": stime}

def parsear_status(pid):
    datos = {}
    with open(f"/proc/{pid}/status") as f:
        for linea in f:
            partes = linea.split(":", 1)
            clave = partes[0].strip()
            valor = partes[1].strip()
            datos[clave] = valor
    return datos
    
def leer_jiffies_sistema():
    with open("/proc/stat") as f:
        linea = f.readline()          # solo la primera línea, la que empieza con "cpu"
    partes = linea.split()            # ['cpu', '398080', '533', ...]
    numeros = partes[1:]              # saltea la etiqueta 'cpu', toma el resto
    total = sum(int(x) for x in numeros)   # suma todos, convertidos a int
    return total

def calcular_cpu(pid, jiffies_ant_proc, jiffies_ant_sist, jiffies_sist_ahora):
    # 1. jiffies actuales del proceso
    d = parsear_stat(pid)
    jiffies_proc_ahora = int(d["utime"]) + int(d["stime"])   # (ojo: ¿tu dict tiene utime/stime?)


    # 3. ¿tenemos lectura anterior de ESTE pid?
    if pid not in jiffies_ant_proc:
        cpu = 0.0
    else:
        delta_proc = jiffies_proc_ahora - jiffies_ant_proc[pid]
        delta_sist = jiffies_sist_ahora - jiffies_ant_sist
        if delta_sist == 0:
            cpu = 0.0
        else:
            cpu = (delta_proc / delta_sist) * 100

    # 4. devolver el cpu% y los valores nuevos para guardar como 'anterior'
    return cpu, jiffies_proc_ahora

def analizador_resumen(shared):
    # historial que sobrevive entre vueltas (privado del analizador)
    jiffies_ant_proc = {}
    jiffies_ant_sist = 0

    while True:
        # (A) leer jiffies del sistema UNA vez por vuelta
        jiffies_sist_ahora = leer_jiffies_sistema()

        # (B) listar PIDs actuales
        pids = [x for x in os.listdir("/proc") if x.isdigit()]

        # (C) armar el super-diccionario de esta vuelta
        resultado = {}
        nuevos_jiffies_proc = {}   # historial nuevo, para la próxima vuelta

        for pid in pids:
            try:
                stat = parsear_stat(pid)
                cpu, jiffies_proc_ahora = calcular_cpu(pid, jiffies_ant_proc, jiffies_ant_sist, jiffies_sist_ahora)
                status = parsear_status(pid)
                resultado[pid] = {
                    'pid': stat['pid'],
                    'comm': stat['comm'],
                    'estado': stat['estado'],
                    'cpu': cpu,
                    'Threads': status['Threads'],
                    'PPid': status['PPid'],
                    'Uid': status['Uid']
                }
                nuevos_jiffies_proc[pid] = jiffies_proc_ahora
            except FileNotFoundError:
                continue

        shared["resumen"] = resultado

        # (D) el resultado nuevo pasa a ser lo que se muestra
        # (E) actualizar historial: lo de ahora es el "anterior" de la próxima
        jiffies_ant_proc = nuevos_jiffies_proc
        jiffies_ant_sist = jiffies_sist_ahora

        # (D) mostrar resultados (temporal, para probar)
        print("\n" + "="*60)
        print(f"{'PID':>7} {'CPU%':>6} {'THR':>4} {'ST':>2}  COMANDO")
        for pid, info in sorted(resultado.items(), key=lambda x: x[1]['cpu'], reverse=True)[:10]:
            print(f"{pid:>7} {info['cpu']:>6.1f} {info['Threads']:>4} {info['estado']:>2}  {info['comm']}")

        # (F) dormir el intervalo
        time.sleep(2)

if __name__ == "__main__":
    manager = Manager()
    shared = manager.dict()

    p = Process(target=analizador_resumen, args=(shared,))   # le paso el dict al hijo
    p.start()
    time.sleep(5)                                    # dejá que el hijo trabaje
    print("\n>>> EL PADRE VE:", len(shared["resumen"]), "procesos")
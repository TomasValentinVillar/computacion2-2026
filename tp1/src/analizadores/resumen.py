import os, time
import signal

from procfs import (parsear_stat, parsear_status, leer_jiffies_sistema, calcular_cpu,
                     leer_cmdline, resolver_usuario)

# la bandera, visible para el handler y para el loop

def analizador_resumen(shared, intervalo):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)
    signal.signal(signal.SIGUSR1, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    jiffies_ant_proc = {}
    jiffies_ant_sist = 0

    while shared["seguir"]:


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
                uid = status['Uid'].split()[0]
                resultado[pid] = {
                    'pid': stat['pid'],
                    'comm': stat['comm'],
                    'cmdline': leer_cmdline(pid) or f"[{stat['comm']}]",
                    'estado': stat['estado'],
                    'cpu': cpu,
                    'Threads': status['Threads'],
                    'PPid': status['PPid'],
                    'Uid': status['Uid'],
                    'Gid': status.get('Gid', ''),
                    'usuario': resolver_usuario(uid),
                }
                nuevos_jiffies_proc[pid] = jiffies_proc_ahora
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue

        shared["resumen"] = resultado

        # (D) el resultado nuevo pasa a ser lo que se muestra
        # (E) actualizar historial: lo de ahora es el "anterior" de la próxima
        jiffies_ant_proc = nuevos_jiffies_proc
        jiffies_ant_sist = jiffies_sist_ahora

        # (D) mostrar resultados (temporal, para probar)
        '''print("\n" + "="*60)
        print(f"{'PID':>7} {'CPU%':>6} {'THR':>4} {'ST':>2}  COMANDO")
        for pid, info in sorted(resultado.items(), key=lambda x: x[1]['cpu'], reverse=True)[:10]:
            print(f"{pid:>7} {info['cpu']:>6.1f} {info['Threads']:>4} {info['estado']:>2}  {info['comm']}")
'''
        # (F) dormir el intervalo
        time.sleep(intervalo.value)


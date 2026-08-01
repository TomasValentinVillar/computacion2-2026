import os, time, signal
from procfs import parsear_stat, leer_jiffies_sistema


def analizador_threads(shared, intervalo):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)
    signal.signal(signal.SIGUSR1, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    jiffies_ant = {}          # historial: {"pid:tid": jiffies_anteriores}
    jiffies_ant_sist = 0      # jiffies del sistema en la vuelta anterior

    while shared["seguir"]:
        jiffies_sist_ahora = leer_jiffies_sistema()   # una vez por vuelta

        pids = [x for x in os.listdir("/proc") if x.isdigit()]
        resultado = {}

        for pid in pids:                              # LOOP EXTERNO: cada proceso
            try:
                tids = os.listdir(f"/proc/{pid}/task")

                threads = {}                          # sub-dict: threads de ESTE proceso
                for tid in tids:                      # LOOP INTERNO: cada thread
                    try:
                        stat = parsear_stat(pid, tid)

                        # --- CPU% del thread (delta de jiffies) ---
                        jiffies_thread = int(stat['utime']) + int(stat['stime'])
                        clave = f"{pid}:{tid}"

                        if clave not in jiffies_ant:
                            cpu = 0.0                 # primera vez: sin lectura anterior
                        else:
                            delta_thread = jiffies_thread - jiffies_ant[clave]
                            delta_sist = jiffies_sist_ahora - jiffies_ant_sist
                            if delta_sist == 0:
                                cpu = 0.0
                            else:
                                cpu = (delta_thread / delta_sist) * 100

                        jiffies_ant[clave] = jiffies_thread   # guardar para la proxima

                        threads[tid] = {
                            'comm': stat['comm'],
                            'estado': stat['estado'],
                            'cpu': cpu,
                        }
                    except (FileNotFoundError, PermissionError, ProcessLookupError):
                        continue

                resultado[pid] = {
                    'num_threads': len(threads),
                    'threads': threads,
                }
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue

        # actualizar el jiffies del sistema UNA vez, al final de la vuelta
        jiffies_ant_sist = jiffies_sist_ahora

        # --- print temporal para verificar ---
        '''print("\n" + "="*60)
        print(f"{'PID':>7} {'#THR':>5} {'maxCPU':>7}  THREADS (tid:nombre:cpu%)")

        def max_cpu(info):
            # el CPU% del thread más activo de este proceso (0 si no tiene threads)
            if not info['threads']:
                return 0.0
            return max(d['cpu'] for d in info['threads'].values())

        for pid, info in sorted(resultado.items(), key=lambda x: max_cpu(x[1]), reverse=True)[:8]:
            muestra = list(info['threads'].items())[:4]
            threads_str = ", ".join(f"{tid}:{d['comm']}:{d['cpu']:.1f}" for tid, d in muestra)
            print(f"{pid:>7} {info['num_threads']:>5} {max_cpu(info):>7.1f}  {threads_str}")'''

        shared["threads"] = resultado
        time.sleep(intervalo.value)
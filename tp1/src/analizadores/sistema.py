import os, time, signal
from procfs import parsear_stat, parsear_status


def analizador_sistema(shared, intervalo):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGUSR1, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    cpu_ant = None      # lectura anterior de la línea cpu (para el delta)

    while shared["seguir"]:
        resultado = {}

        # --- uptime ---
        with open("/proc/uptime") as f:
            datos = f.read().split()
        resultado["uptime_segundos"] = int(float(datos[0]))

        # --- meminfo ---
        meminfo = {}
        with open("/proc/meminfo") as f:
            for linea in f:
                partes = linea.split(":", 1)
                meminfo[partes[0].strip()] = partes[1].strip()
        resultado["mem_total"] = meminfo["MemTotal"]
        resultado["mem_free"] = meminfo["MemFree"]
        resultado["mem_disponible"] = meminfo["MemAvailable"]
        resultado["mem_buffers"] = meminfo.get("Buffers", "0 kB")
        resultado["mem_cached"] = meminfo.get("Cached", "0 kB")
        resultado["swap_total"] = meminfo.get("SwapTotal", "0 kB")
        resultado["swap_free"] = meminfo.get("SwapFree", "0 kB")

        # --- loadavg ---
        with open("/proc/loadavg") as f:
            load = f.read().split()
        resultado["load_1min"] = load[0]
        resultado["load_5min"] = load[1]
        resultado["load_15min"] = load[2]

        # --- boot time (btime en /proc/stat) ---
        with open("/proc/stat") as f:
            for linea in f:
                if linea.startswith("btime"):
                    resultado["boot_time"] = int(linea.split()[1])
                    break

        # --- conteos: recorrer /proc una vez y contar ---
        total = 0
        por_estado = {}
        threads_total = 0
        zombies = 0
        for pid in [x for x in os.listdir("/proc") if x.isdigit()]:
            try:
                stat = parsear_stat(pid)
                total += 1
                estado = stat['estado']
                por_estado[estado] = por_estado.get(estado, 0) + 1
                if estado == 'Z':
                    zombies += 1
                status = parsear_status(pid)
                threads_total += int(status.get('Threads', '1'))
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue

        resultado["procesos_total"] = total
        resultado["procesos_por_estado"] = dict(por_estado)
        resultado["threads_total"] = threads_total
        resultado["zombies"] = zombies

                # --- top 3 por CPU (del resumen) ---
        resumen = shared.get("resumen", {})
        top_cpu = sorted(resumen.items(), key=lambda x: x[1]['cpu'], reverse=True)[:3]
        resultado["top_cpu"] = [(pid, info['comm'], info['cpu']) for pid, info in top_cpu]

        # --- top 3 por memoria (del memoria, por VmRSS) ---
        memoria = shared.get("memoria", {})
        def rss(info):
            v = info.get('VmRSS', '')
            return int(v.split()[0]) if v else 0
        top_mem = sorted(memoria.items(), key=lambda x: rss(x[1]), reverse=True)[:3]
        resultado["top_mem"] = [(pid, info['comm'], info['VmRSS']) for pid, info in top_mem]

        # --- CPU global (delta de /proc/stat linea cpu) ---
        with open("/proc/stat") as f:
            campos = f.readline().split()      # ['cpu', user, nice, system, idle, ...]
        # campos[0] es 'cpu', los numeros arrancan en campos[1]
        nums = [int(x) for x in campos[1:8]]   # user,nice,system,idle,iowait,irq,softirq
        cpu_ahora = nums

        if cpu_ant is not None:
            deltas = [ahora - antes for ahora, antes in zip(cpu_ahora, cpu_ant)]
            total = sum(deltas)
            if total > 0:
                resultado["cpu_user"] = round((deltas[0] + deltas[1]) / total * 100, 1)  # user+nice
                resultado["cpu_system"] = round(deltas[2] / total * 100, 1)
                resultado["cpu_idle"] = round(deltas[3] / total * 100, 1)
                resultado["cpu_iowait"] = round(deltas[4] / total * 100, 1)

        cpu_ant = cpu_ahora     # guardar para la próxima vuelta

        shared["sistema"] = resultado
        time.sleep(intervalo.value)
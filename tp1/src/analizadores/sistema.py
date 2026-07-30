import os, time, signal


def analizador_sistema(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while shared["seguir"]:
        resultado = {}

        # --- uptime ---
        with open("/proc/uptime") as f:
            datos = f.read().split()
        segundos = int(float(datos[0]))
        resultado["uptime_segundos"] = segundos

        # --- meminfo ---
        meminfo = {}
        with open("/proc/meminfo") as f:
            for linea in f:
                partes = linea.split(":", 1)
                clave = partes[0].strip()
                valor = partes[1].strip()
                meminfo[clave] = valor
        resultado["mem_total"] = meminfo["MemTotal"]
        resultado["mem_free"] = meminfo["MemFree"]
        resultado["mem_disponible"] = meminfo["MemAvailable"]

        # --- loadavg ---
        with open("/proc/loadavg") as f:
            load = f.read().split()
        resultado["load_1min"] = load[0]
        resultado["load_5min"] = load[1]
        resultado["load_15min"] = load[2]

        shared["sistema"] = resultado

        # --- print temporal ---
        # convertir uptime a h/m/s legible
        h = segundos // 3600
        m = (segundos % 3600) // 60
        s = segundos % 60

        print("\n" + "=" * 50)
        print("           ESTADO DEL SISTEMA")
        print("=" * 50)
        print(f"  Uptime      : {h}h {m}m {s}s")
        print(f"  RAM total   : {resultado['mem_total']}")
        print(f"  RAM libre   : {resultado['mem_free']}")
        print(f"  RAM disp.   : {resultado['mem_disponible']}")
        print(f"  Load (1/5/15): {resultado['load_1min']} / "
              f"{resultado['load_5min']} / {resultado['load_15min']}")

        time.sleep(2)
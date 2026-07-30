import os, time, signal
from procfs import tipo_fd

def analizador_fds(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while shared["seguir"]:
        pids = [x for x in os.listdir("/proc") if x.isdigit()]

        resultado = {}

        for pid in pids:
            try:
                fds = os.listdir(f"/proc/{pid}/fd")
                fd_info = {}
                for fd in fds:
                    try:
                        destino = os.readlink(f"/proc/{pid}/fd/{fd}")
                        fd_info[fd] = {
                            'destino': destino,
                            'tipo': tipo_fd(destino)
                        }
                    except (FileNotFoundError, PermissionError):
                        continue
                resultado[pid] = fd_info
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue

        print("\n" + "="*70)
        print(f"{'PID':>7} {'#FDs':>5} {'Tipos de FDs'}")
        for pid, info in sorted(resultado.items(), key=lambda x: int(x[0]))[:15]:
            tipos = {}
            for fd_data in info.values():
                tipo = fd_data['tipo']
                tipos[tipo] = tipos.get(tipo, 0) + 1
            tipos_str = ", ".join(f"{k}:{v}" for k, v in tipos.items())
            print(f"{pid:>7} {len(info):>5} {tipos_str}")
        shared["fds"] = resultado
        time.sleep(2)
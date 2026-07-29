import os, time
import signal

from procfs import parsear_status, parsear_stat, parsear_maps

def analizador_memoria(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while shared["seguir"]:
        # (A) listar PIDs actuales
        pids = [x for x in os.listdir("/proc") if x.isdigit()]

        # (B) armar el super-diccionario de esta vuelta
        resultado = {}

        for pid in pids:
            try:
                status = parsear_status(pid)
                stat = parsear_stat(pid)
                maps = parsear_maps(pid)
                resultado[pid] = {
                    'pid': pid,
                    'VmSize': status.get('VmSize', '0 kB'),
                    'VmRSS': status.get('VmRSS', '0 kB'),
                    'VmData': status.get('VmData', '0 kB'),
                    'VmStk': status.get('VmStk', '0 kB'),
                    'VmExe': status.get('VmExe', '0 kB'),
                    'Threads': status.get('Threads', '0'),
                    'VmHWM': status.get('VmHWM', '0 kB'),
                    'VmSwap': status.get('VmSwap', '0 kB'),
                    'VmLib': status.get('VmLib', '0 kB'),
                    'minflt': stat['minflt'],
                    'majflt': stat['majflt'],
                    'text': maps['text'],
                    'data': maps['data'],
                    'heap': maps['heap'],
                    'stack': maps['stack'],
                    'shared': maps['shared']
                }
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue

        #print(f"TOTAL procesos parseados: {len(resultado)}")
        print(f"{'PID':>7} {'VmRSS':>10} {'text':>10} {'data':>10} {'heap':>10} {'stack':>10} {'shared':>10}")
        for pid, info in sorted(resultado.items(), key=lambda x: int(x[1]['VmRSS'].split()[0]), reverse=True)[:10]:
            print(f"{pid:>7} {info['VmRSS']:>10} {info['text']:>10} {info['data']:>10} {info['heap']:>10} {info['stack']:>10} {info['shared']:>10}")
        shared["memoria"] = resultado
        time.sleep(2)

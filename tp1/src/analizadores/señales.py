import os, time, signal
from procfs import parsear_status, decodificar_senales, parsear_stat

def analizador_senales(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while shared["seguir"]:
        pids = [x for x in os.listdir("/proc") if x.isdigit()]

        resultado = {}

        for pid in pids:
            try:
                status = parsear_status(pid)
                stat = parsear_stat(pid)
                resultado[pid] = {
                    'SigBlk': decodificar_senales(status.get('SigBlk', '0')),
                    'SigIgn': decodificar_senales(status.get('SigIgn', '0')),
                    'SigCgt': decodificar_senales(status.get('SigCgt', '0')),
                    'SigPnd': decodificar_senales(status.get('SigPnd', '0')),
                    'comm' : stat['comm']
                }
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
        '''print("\n" + "="*70)
        print(f"{'PID':>7} {'#Blk':>5} {'#Ign':>5} {'#Cgt':>5} {'#Pnd':>5}  SigCgt (con handler)")
        for pid, info in sorted(resultado.items(), key=lambda x: int(x[0]))[:15]:
            cgt = ", ".join(info['SigCgt'][:5])          # solo las primeras 5 para que entre
            print(f"{pid:>7} {len(info['SigBlk']):>5} {len(info['SigIgn']):>5} {len(info['SigCgt']):>5} {len(info['SigPnd']):>5}  {cgt}")'''
        shared["senales"] = resultado
        time.sleep(2)
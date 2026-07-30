import os, time
import signal

from procfs import parsear_stat, parsear_status

POLICIES = {
    "0": "OTHER",
    "1": "FIFO",
    "2": "RR",
    "3": "BATCH",
    "5": "IDLE",
}
def analizador_scheduling(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while shared["seguir"]:

        pids = [x for x in os.listdir("/proc") if x.isdigit()]
        resultado = {}

        for pid in pids:
            try:
                stat = parsear_stat(pid)
                status = parsear_status(pid)
                resultado[pid] = {
                    'priority': stat['priority'],
                    'nice': stat['nice'],
                    'policy': POLICIES.get(stat['policy'], stat['policy']),
                    'voluntary_ctxt_switches': status['voluntary_ctxt_switches'],
                    'nonvoluntary_ctxt_switches': status['nonvoluntary_ctxt_switches'],
                    'pgid': stat['pgid'],
                    'sid': stat['sid'],
                    'affinity': list(os.sched_getaffinity(int(pid)))
                }
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue

        shared["scheduling"] = resultado
        '''print("\n" + "="*60)
        print(f"{'PID':>7} {'PRIO':>5} {'NICE':>5} {'POLICY':>10} {'VOLUNTARY':>10} {'NONVOLUNTARY':>15} {'PGID':>7} {'SID':>7} {'AFFINITY':>20}")
        for pid, info in sorted(resultado.items(), key=lambda x: (int(x[1]['priority']), int(x[1]['nice'])), reverse=True)[:10]:
            print(f"{pid:>7} {info['priority']:>5} {info['nice']:>5} {info['policy']:>10} {info['voluntary_ctxt_switches']:>10} {info['nonvoluntary_ctxt_switches']:>15} {info['pgid']:>7} {info['sid']:>7} {str(info['affinity']):>20}")'''
        time.sleep(2)
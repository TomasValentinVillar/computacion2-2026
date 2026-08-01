import signal
import time
from multiprocessing import Process, Manager
from analizadores.resumen import analizador_resumen
from analizadores.memoria import analizador_memoria
from analizadores.señales import analizador_senales
from analizadores.fds import analizador_fds
from analizadores.threads import analizador_threads
from analizadores.scheduling import analizador_scheduling
from analizadores.sistema import analizador_sistema
from display import display
from multiprocessing import Value

cerrar = False

def manejador(signum, frame):
    global cerrar
    cerrar = True

if __name__ == "__main__":
    signal.signal(signal.SIGINT, manejador)
    signal.signal(signal.SIGTERM, manejador)

    manager = Manager()
    shared = manager.dict()
    shared["seguir"] = True

    intervalos = {
    "resumen": Value('i', 2),
    "memoria": Value('i', 3),
    "fds": Value('i', 5),
    "threads": Value('i', 2),
    "senales": Value('i', 10),
    "scheduling": Value('i', 10),
    "sistema": Value('i', 2),
    }

    # lista de procesos (escalable: mañana agregás más analizadores acá)
    procesos = [
        Process(target=analizador_resumen, args=(shared, intervalos["resumen"])),
        Process(target=analizador_memoria, args=(shared, intervalos["memoria"])),
        Process(target=analizador_senales, args=(shared, intervalos["senales"])),
        Process(target=analizador_fds, args=(shared, intervalos["fds"])),
        Process(target=analizador_threads, args=(shared, intervalos["threads"])),
        Process(target=analizador_scheduling, args=(shared, intervalos["scheduling"])),
        Process(target=analizador_sistema, args=(shared, intervalos["sistema"])),
        Process(target=display, args=(shared, intervalos)),
    ]

    # lanzar TODOS
    for p in procesos:
        p.start()

    # esperar la señal
    while not cerrar:
        time.sleep(0.5)
        #if "resumen" in shared and "memoria" in shared:
        #    print(f">>> resumen: {len(shared['resumen'])} procs | memoria: {len(shared['memoria'])} procs")


    # cierre ordenado
    print("\ncerrando...")
    shared["seguir"] = False
    for p in procesos:      # esperar TODOS
        p.join()
    print("cerrado limpio")
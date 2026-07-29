import signal
import time
from multiprocessing import Process, Manager
from analizadores.resumen import analizador_resumen
from analizadores.memoria import analizador_memoria
from analizadores.señales import analizador_senales

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

    # lista de procesos (escalable: mañana agregás más analizadores acá)
    procesos = [
        Process(target=analizador_resumen, args=(shared,)),
        Process(target=analizador_memoria, args=(shared,)),
        Process(target=analizador_senales, args=(shared,))
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
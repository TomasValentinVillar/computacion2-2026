import signal
from multiprocessing import Process, Manager
import time
from analizadores.resumen import analizador_resumen

cerrar = False

def manejador(signum, frame):
    global cerrar
    cerrar = True          # ← lo ÚNICO que hace el handler: levantar la bandera}

if __name__ == "__main__":
    signal.signal(signal.SIGINT, manejador)
    signal.signal(signal.SIGTERM, manejador)

    manager = Manager()
    shared = manager.dict()
    shared["seguir"] = True          # ← la bandera arranca en True

    p = Process(target=analizador_resumen, args=(shared,))
    p.start()

    while not cerrar:
        time.sleep(0.5)

    print("\ncerrando...")
    shared["seguir"] = False         # ← le pedís al hijo que pare
    p.join()                         # ← ahora el hijo SÍ va a terminar
    print("cerrado limpio")
import time, signal
from multiprocessing import Process, Manager

cerrar = False

def manejador(signum, frame):
    global cerrar
    cerrar = True

def hijo(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    while True:
        shared["dato"] = "algo"        # escribe en el Manager, como el analizador
        print("hijo trabajando...")
        time.sleep(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, manejador)
    manager = Manager()
    shared = manager.dict()
    p = Process(target=hijo, args=(shared,))
    p.start()

    while not cerrar:
        time.sleep(0.5)

    print("\ncerrando...")
    p.terminate()
    p.join()
    print("cerrado limpio")
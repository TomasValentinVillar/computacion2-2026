import multiprocessing
import time
import random

def worker(id):
    print(f"[Worker-{id}] arranca")
    time.sleep(random.uniform(0.5, 2))
    print(f"[Worker-{id}] termina")

if __name__ == "__main__":
    procesos = []
    inicio = time.time()
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        p.start()
        procesos.append(p)

    for p in procesos:
        p.join()
    duracion = time.time() - inicio
    print(f"[Main] todos terminaron en {duracion:.2f}s")
import multiprocessing
import time
import sys

def worker():
    pass  # no hace nada, solo medimos el costo de crear el proceso

def medir(metodo, n=100):
    ctx = multiprocessing.get_context(metodo)
    
    inicio = time.time()
    procesos = []
    for i in range(n):
        p = ctx.Process(target=worker)
        p.start()
        procesos.append(p)
    for p in procesos:
        p.join()
    duracion = time.time() - inicio
    
    print(f"[{metodo}] {n} procesos en {duracion:.2f}s ({duracion/n*1000:.1f}ms por proceso)")

if __name__ == "__main__":
    medir('fork')
    medir('spawn')
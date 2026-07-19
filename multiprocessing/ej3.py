import multiprocessing
import time

def productor(q):
    for i in range(5):
        q.put(f"item-{i}")
        time.sleep(0.1)
    q.put(None)  # señal de fin

def consumidor(q):
    while True:
        item = q.get()
        if item is None:
            break
        print(f"Consumió: {item}")

if __name__ == "__main__":
    q = multiprocessing.Queue()

    p1 = multiprocessing.Process(target=productor, args=(q,))
    p2 = multiprocessing.Process(target=consumidor, args=(q,))

    p1.start(); p2.start()
    p1.join(); p2.join()
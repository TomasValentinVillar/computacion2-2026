from concurrent.futures import ThreadPoolExecutor

def trabajo(n):
    return n * n

dato = 7

if __name__ == "__main__0":

    with ThreadPoolExecutor(4) as pool:      # cambiar a ProcessPoolExecutor
        futuro = pool.submit(trabajo, dato)  # y todo lo demás sigue igual
        print(futuro.result())
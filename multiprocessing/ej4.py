import multiprocessing

def hijo(conn):
    for i in range(5):
        msg = conn.recv()                    # espera ping del padre
        print(f"[Hijo] recibió: {msg}")
        conn.send(f"pong-{i}")               # responde
    conn.close()

if __name__ == "__main__":
    padre_conn, hijo_conn = multiprocessing.Pipe()
    p = multiprocessing.Process(target=hijo, args=(hijo_conn,))
    p.start()
    
    for i in range(5):
        padre_conn.send(f"ping-{i}")         # padre tira ping
        msg = padre_conn.recv()              # espera pong
        print(f"[Padre] recibió: {msg}")
    
    padre_conn.close()
    p.join()
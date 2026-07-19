import os
import time

pid = os.fork()
v = 5

if pid == 0:
    v = 6
    print(f"Hijo: PID={os.getpid()}, v={v}, {id(v)}")

else:
    os.wait()
    print(f"Padre: PID={os.getpid()}, v={v},{id(v)}")
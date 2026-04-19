import redis
import os
import time

redis_host = os.getenv('REDIS_HOST', 'localhost')
r = redis.Redis(host=redis_host, port=6379)

print(f"Conectando a Redis en {redis_host}...")

while True:
    contador = r.incr('contador')
    print(f"Worker: contador en {contador}")
    time.sleep(2)
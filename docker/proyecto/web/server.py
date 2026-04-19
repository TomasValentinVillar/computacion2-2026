import redis
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

redis_host = os.getenv('REDIS_HOST', 'localhost')
r = redis.Redis(host=redis_host, port=6379)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        contador = r.get('contador')
        if contador:
            contador = contador.decode()
        else:
            contador = 0
        respuesta = f"Contador actual: {contador}".encode()
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(respuesta)

print("Servidor en puerto 8000...")
HTTPServer(('0.0.0.0', 8000), Handler).serve_forever()

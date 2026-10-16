import os
import socketserver
import threading

class Eco(socketserver.StreamRequestHandler):
    def setup(self):
        print('setup')
        super().setup()

    def handle(self):
        print('handle')
        with self.server.lock:
            self.server.n += 1
            n = self.server.n

        self.wfile.write(f'visita {n}\n'.encode())
        print(os.getpid())
        for linea in self.rfile:
            if linea.strip() == b'CRASH':
                raise RuntimeError('explotó')
            self.wfile.write(b'recibi ' + linea.strip() + b'\n')
    
    def finish(self):
        print('finish')
        super().finish()
    


class ServidorThread(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    n = 0
    lock = threading.Lock()   # import threading

    def handle_error(self, request, client_address):
        print('handle_error')
        super().handle_error(request, client_address)


class ServidorFork(socketserver.ForkingTCPServer):
    allow_reuse_address = True

ServidorThread(('localhost',8080),Eco).serve_forever()
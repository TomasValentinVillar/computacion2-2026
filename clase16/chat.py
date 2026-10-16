#!/usr/bin/env python3
"""comandos.py extendido: NICK, BROADCAST, tolerancia a desconexiones y timeout.

Comandos: TIME, ECHO <texto>, NICK <nombre>, QUIEN, BROADCAST <texto>,
          CONTADOR, AYUDA, QUIT

Uso:
    python3 chat.py              # normal
    python3 chat.py --retardo    # agranda la ventana del punto 3 (3 segundos)
    nc localhost 8080
"""
import socketserver
import sys
import threading
import time

INACTIVIDAD = 30                       # segundos sin mandar nada -> afuera
RETARDO = 3 if '--retardo' in sys.argv else 0


class Handler(socketserver.StreamRequestHandler):
    # Configuración por herencia: StreamRequestHandler.setup() hace
    # self.connection.settimeout(self.timeout)
    timeout = INACTIVIDAD

    def setup(self):
        super().setup()                       # crea rfile/wfile y aplica timeout
        self.nick = f'{self.client_address[0]}:{self.client_address[1]}'
        self.lock_envio = threading.Lock()    # un escritor a la vez en MI socket
        with self.server.lock:
            self.server.conexiones += 1
            self.server.clientes[self.client_address] = self

    def finish(self):
        with self.server.lock:
            self.server.clientes.pop(self.client_address, None)
        super().finish()

    def enviar(self, texto):
        """Único punto de escritura: lo usan este thread y los de broadcast."""
        with self.lock_envio:
            self.wfile.write((texto + '\n').encode())

    def broadcast(self, texto):
        # Paso 1: copiar destinatarios con el lock del servidor (rápido)
        with self.server.lock:
            destinos = [h for h in self.server.clientes.values() if h is not self]

        if RETARDO:
            print(f'(broadcast de {self.nick}: esperando {RETARDO}s antes de enviar)')
            time.sleep(RETARDO)

        # Paso 2: enviar SIN el lock del servidor (lento, es red)
        mensaje = f'[{self.nick}] {texto}'
        enviados = 0
        for h in destinos:
            try:
                h.enviar(mensaje)
                enviados += 1
            except (OSError, ValueError) as e:
                # Se fue entre el paso 1 y el 2: lo salteamos y seguimos
                print(f'  no se pudo enviar a {h.nick}: {e!r}')
        return enviados, len(destinos)

    def handle(self):
        self.enviar('Servidor de comandos. Escribí AYUDA.')
        try:
            for linea in self.rfile:
                if not self.procesar(linea):
                    return                          # QUIT
        except TimeoutError:
            print(f'{self.nick} desconectado por inactividad')
            try:
                self.enviar(f'Desconectado por {INACTIVIDAD}s sin actividad')
            except (OSError, ValueError):
                pass

    def procesar(self, linea):
        """Devuelve False si hay que cerrar la conexión."""
        partes = linea.decode('utf-8', 'replace').strip().split(maxsplit=1)
        if not partes:
            return True
        cmd, resto = partes[0].upper(), (partes[1] if len(partes) > 1 else '')

        if cmd == 'TIME':
            self.enviar(time.strftime('%Y-%m-%d %H:%M:%S'))
        elif cmd == 'ECHO':
            self.enviar(resto)
        elif cmd == 'NICK':
            if not resto:
                self.enviar('Uso: NICK <nombre>')
            else:
                with self.server.lock:              # otros lo leen en QUIEN
                    viejo, self.nick = self.nick, resto
                self.enviar(f'Ahora sos {self.nick} (antes {viejo})')
        elif cmd == 'QUIEN':
            with self.server.lock:
                nicks = sorted(h.nick for h in self.server.clientes.values())
            self.enviar(f'{len(nicks)} conectados: ' + ', '.join(nicks))
        elif cmd == 'BROADCAST':
            if not resto:
                self.enviar('Uso: BROADCAST <texto>')
            else:
                ok, total = self.broadcast(resto)
                self.enviar(f'Enviado a {ok} de {total}')
        elif cmd == 'CONTADOR':
            with self.server.lock:
                n = self.server.conexiones
            self.enviar(f'Conexiones totales desde el arranque: {n}')
        elif cmd == 'AYUDA':
            self.enviar('TIME | ECHO <t> | NICK <n> | QUIEN | BROADCAST <t> | CONTADOR | QUIT')
        elif cmd == 'QUIT':
            self.enviar('Chau')
            return False
        else:
            self.enviar(f'Comando desconocido: {cmd}')
        return True


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conexiones = 0
        self.clientes = {}                 # dirección -> handler
        self.lock = threading.Lock()

    def handle_error(self, request, client_address):
        import traceback
        ultima = traceback.format_exc().strip().splitlines()[-1]
        print(f'[ERROR] {client_address}: {ultima}')


if __name__ == '__main__':
    with Servidor(('0.0.0.0', 8080), Handler) as srv:
        print(f'Escuchando en 0.0.0.0:8080 (timeout {INACTIVIDAD}s'
              f'{", retardo " + str(RETARDO) + "s" if RETARDO else ""})')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor detenido')

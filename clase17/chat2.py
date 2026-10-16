#!/usr/bin/env python3
"""Chat multiusuario con selectors, con /nick, /lista y framing por líneas.

Uso:
    python3 chat2.py [puerto]

Y desde varias terminales:
    nc localhost 8080
"""
import selectors
import socket
import sys

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

sel = selectors.DefaultSelector()
clientes = {}           # socket -> apodo
salida = {}             # socket -> bytes pendientes de enviar
entrada = {}            # socket -> bytes recibidos que todavía no forman una línea


def enviar_a(conn, mensaje: bytes):
    """Encola un mensaje para UN cliente y prende su aviso de escritura."""
    salida[conn] = salida.get(conn, b'') + mensaje
    sel.modify(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, manejar)


def difundir(mensaje: bytes, excepto=None):
    """Encola un mensaje para todos los clientes menos uno."""
    for conn in clientes:
        if conn is not excepto:
            enviar_a(conn, mensaje)


def aceptar(servidor, _mascara):
    conn, direccion = servidor.accept()
    conn.setblocking(False)
    apodo = f'{direccion[0]}:{direccion[1]}'
    clientes[conn] = apodo
    entrada[conn] = b''
    sel.register(conn, selectors.EVENT_READ, manejar)
    print(f'+ {apodo}  ({len(clientes)} conectados)')
    enviar_a(conn, b'Bienvenido al chat. Comandos: /nick <nombre>, /lista\n')
    difundir(f'* se conecto {apodo}\n'.encode(), excepto=conn)


def desconectar(conn):
    apodo = clientes.pop(conn, '?')
    salida.pop(conn, None)
    entrada.pop(conn, None)
    sel.unregister(conn)            # SIEMPRE antes de close()
    conn.close()
    print(f'- {apodo}  ({len(clientes)} conectados)')
    difundir(f'* se fue {apodo}\n'.encode())


def procesar_linea(conn, linea: bytes):
    """Una línea completa (sin el \\n): comando o mensaje."""
    apodo = clientes.get(conn, '?')
    # Decodificar recién acá, con la línea entera: así una letra con tilde
    # partida entre dos recv() no se rompe. rstrip('\r') por si el cliente
    # manda \r\n.
    texto = linea.decode('utf-8', errors='replace').rstrip('\r')
    if not texto:
        return

    if texto == '/nick' or texto.startswith('/nick '):
        nuevo = texto[6:].strip()
        if not nuevo:
            enviar_a(conn, b'* uso: /nick <nombre>\n')
            return
        clientes[conn] = nuevo
        print(f'  * {apodo} ahora es {nuevo}')
        enviar_a(conn, f'* ahora sos {nuevo}\n'.encode())
        difundir(f'* {apodo} ahora es {nuevo}\n'.encode(), excepto=conn)
        return

    if texto == '/lista':
        nombres = ', '.join(clientes.values())
        enviar_a(conn, f'* conectados ({len(clientes)}): {nombres}\n'.encode())
        return

    print(f'  <{apodo}> {texto}')
    difundir(f'<{apodo}> {texto}\n'.encode(), excepto=conn)


def manejar(conn, mascara):
    """Un solo handler para lectura y escritura."""
    if mascara & selectors.EVENT_READ:
        try:
            datos = conn.recv(4096)
        except ConnectionResetError:
            desconectar(conn)
            return
        if not datos:
            desconectar(conn)
            return
        # Framing: lo nuevo se suma a lo que ya había, y se procesan
        # TODAS las líneas completas (pueden ser cero, una o varias).
        # Lo que no tiene \n todavía queda en el buffer para el próximo recv().
        entrada[conn] += datos
        while b'\n' in entrada[conn]:
            linea, entrada[conn] = entrada[conn].split(b'\n', 1)
            procesar_linea(conn, linea)

    if mascara & selectors.EVENT_WRITE:
        buf = salida.get(conn, b'')
        if buf:
            try:
                n = conn.send(buf)
            except (BrokenPipeError, ConnectionResetError):
                desconectar(conn)
                return
            salida[conn] = buf[n:]
        if not salida.get(conn) and conn in clientes:
            sel.modify(conn, selectors.EVENT_READ, manejar)


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', PUERTO))
    servidor.listen(128)
    servidor.setblocking(False)
    sel.register(servidor, selectors.EVENT_READ, aceptar)

    print(f'Chat escuchando en 0.0.0.0:{PUERTO} ({type(sel).__name__})')
    print('Conectate con: nc localhost', PUERTO)

    try:
        while True:
            for clave, mascara in sel.select():
                clave.data(clave.fileobj, mascara)
    except KeyboardInterrupt:
        print('\nChat detenido')
    finally:
        sel.close()


if __name__ == '__main__':
    main()

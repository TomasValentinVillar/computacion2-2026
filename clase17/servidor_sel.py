#!/usr/bin/env python3
"""servidor_select.py reescrito con selectors.

Uso:
    python3 servidor_sel.py [puerto]            # DefaultSelector
    python3 servidor_sel.py --select [puerto]   # forzar SelectSelector
"""
import selectors
import socket
import sys

usar_select = '--select' in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith('--')]
PUERTO = int(args[0]) if args else 8080

sel = selectors.SelectSelector() if usar_select else selectors.DefaultSelector()


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', PUERTO))
    servidor.listen(128)
    servidor.setblocking(False)
    # El dato asociado distingue: None = el que escucha, una tupla = un cliente
    sel.register(servidor, selectors.EVENT_READ, None)
    print(f'Escuchando en 0.0.0.0:{PUERTO} con {type(sel).__name__}')

    try:
        while True:
            for clave, _mascara in sel.select():
                sock = clave.fileobj
                if clave.data is None:
                    conn, direccion = servidor.accept()
                    conn.setblocking(False)
                    # La dirección viaja guardada en el selector
                    sel.register(conn, selectors.EVENT_READ, direccion)
                    print(f'+ cliente {direccion}  (total: {len(sel.get_map()) - 1})')
                else:
                    datos = sock.recv(4096)
                    if datos:
                        sock.sendall(datos)
                    else:
                        sel.unregister(sock)
                        sock.close()
                        print(f'- cliente {clave.data}  (total: {len(sel.get_map()) - 1})')
    except KeyboardInterrupt:
        print('\nServidor detenido')
    finally:
        for clave in list(sel.get_map().values()):
            clave.fileobj.close()
        sel.close()


if __name__ == '__main__':
    main()

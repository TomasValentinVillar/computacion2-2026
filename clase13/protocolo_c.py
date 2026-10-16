import struct

def recibir_exacto(sock, n):
    """Lee EXACTAMENTE n bytes, o None si cerraron antes.
    PISTA: recv(n) puede devolver menos de n. Hay que insistir."""
    datos = b''
    while len(datos) < n:
        pedazo = sock.recv(n - len(datos))     # pido lo que me falta
        if not pedazo:
            return None                         # cerró antes de completar
        datos += pedazo
    return datos

def enviar_mensaje(sock, payload: bytes):
    sock.sendall(struct.pack('!I', len(payload)) + payload)

def recibir_mensaje(sock):
    cabecera = recibir_exacto(sock, 4)          # leo 4 bytes de cabecera
    if cabecera is None:
        return None
    (longitud,) = struct.unpack('!I', cabecera) # desempaco el largo
    return recibir_exacto(sock, longitud)       # leo esa cantidad exacta
def parsear_status(pid):
    datos = {}
    with open(f"/proc/{pid}/status") as f:
        for linea in f:
            partes = linea.split(":", 1)
            clave = partes[0].strip()
            valor = partes[1].strip()
            datos[clave] = valor
    return datos
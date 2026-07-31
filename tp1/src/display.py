import curses
import signal


# ---------------------------------------------------------------------------
# Funciones de dibujo: una por vista. Cada una recibe la pantalla, los datos
# de esa vista (leidos del shared) y las dimensiones, y dibuja su tabla.
# ---------------------------------------------------------------------------

def ordenar_vista(vista_clave, datos):
    """Devuelve la lista [(pid, info), ...] ordenada segun la vista.
    UNICA fuente del orden: la usan tanto el dibujo como el pin, asi el
    indice 'seleccion' significa lo mismo en los dos lados."""

    if vista_clave == "resumen":
        return sorted(datos.items(), key=lambda x: x[1]['cpu'], reverse=True)

    elif vista_clave == "memoria":
        return sorted(datos.items(),
                      key=lambda x: int(x[1]['VmRSS'].split()[0]), reverse=True)

    elif vista_clave == "senales":
        return sorted(datos.items(), key=lambda x: len(x[1]['SigCgt']), reverse=True)

    elif vista_clave == "fds":
        return sorted(datos.items(), key=lambda x: int(x[0]))

    elif vista_clave == "threads":
        def max_cpu(info):
            if not info['threads']:
                return 0.0
            return max(d['cpu'] for d in info['threads'].values())
        return sorted(datos.items(), key=lambda x: max_cpu(x[1]), reverse=True)

    elif vista_clave == "scheduling":
        return sorted(datos.items(),
                      key=lambda x: (int(x[1]['priority']), int(x[1]['nice'])),
                      reverse=True)

    else:
        return list(datos.items())

# --- dibujar_resumen: ahora recibe offset y dibuja solo la tajada visible ---

def dibujar_resumen(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles):
    header = f"{'PID':>7} {'CPU%':>6} {'THR':>4} {'ST':>3}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    # tajada visible: desde offset, tantos como entren
    visibles = procesos[offset : offset + filas_visibles]

    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i       # el indice real en la lista completa
        linea = (f"{pid:>7} {info['cpu']:>6.1f} "
                 f"{info['Threads']:>4} {info['estado']:>3}  {info['comm']}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1


def dibujar_memoria(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles):
    header = f"{'PID':>7} {'VmRSS':>12} {'VmSize':>12} {'minflt':>10} {'majflt':>8}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    # ordenar por VmRSS (ojo: es string tipo '1804 kB', hay que convertir)

    # tajada visible: desde offset, tantos como entren
    visibles = procesos[offset : offset + filas_visibles]

    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        linea = (f"{pid:>7} {info['VmRSS']:>12} {info['VmSize']:>12} "
                 f"{info['minflt']:>10} {info['majflt']:>8}  {info['comm']}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_senales(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles):
    header = f"{'PID':>7} {'SigBlk':>10} {'SigIgn':>10} {'SigCgt':>10} {'SigPnd':>10}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    # tajada visible: desde offset, tantos como entren
    visibles = procesos[offset : offset + filas_visibles]

    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        linea = (f"{pid:>7} {len(info['SigBlk']):>10} {len(info['SigIgn']):>10} "
                 f"{len(info['SigCgt']):>10} {len(info['SigPnd']):>10}  {info['comm']}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_fds(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles):
    header = f"{'PID':>7} {'#FDs':>5} {'Tipos de FDs'}"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    # tajada visible: desde offset, tantos como entren
    visibles = procesos[offset : offset + filas_visibles]

    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        tipos = {}
        for fd_data in info.values():
            tipo = fd_data['tipo']
            tipos[tipo] = tipos.get(tipo, 0) + 1 # contar cuántos de cada tipo
        tipos_str = ", ".join(f"{k}:{v}" for k, v in tipos.items()) # crear string de tipos
        linea = f"{pid:>7} {len(info):>5} {tipos_str}"
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_threads(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles):
    header = f"{'PID':>7} {'#THR':>5} {'maxCPU':>7}  THREADS (tid:nombre:cpu%)"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    def max_cpu(info):
        # el CPU% del thread más activo de este proceso (0 si no tiene threads)
        if not info['threads']:
            return 0.0
        return max(d['cpu'] for d in info['threads'].values())

    # tajada visible: desde offset, tantos como entren
    visibles = procesos[offset : offset + filas_visibles]

    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        muestra = list(info['threads'].items())[:4] # mostrar solo los primeros 4 threads
        threads_str = ", ".join(f"{tid}:{d['comm']}:{d['cpu']:.1f}" for tid, d in muestra)
        linea = f"{pid:>7} {info['num_threads']:>5} {max_cpu(info):>7.1f}  {threads_str}"
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_scheduling(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles):
    header = f"{'PID':>7} {'PRIO':>5} {'NICE':>5} {'POLICY':>10} {'VOLUNTARY':>10} {'NONVOLUNTARY':>15} {'PGID':>7} {'SID':>7} {'AFFINITY':>20}"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    # tajada visible: desde offset, tantos como entren
    visibles = procesos[offset : offset + filas_visibles]

    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        affinity_str = str(info['affinity'])
        linea = (f"{pid:>7} {info['priority']:>5} {info['nice']:>5} "
                 f"{info['policy']:>10} {info['voluntary_ctxt_switches']:>10} "
                 f"{info['nonvoluntary_ctxt_switches']:>15} {info['pgid']:>7} "
                 f"{info['sid']:>7} {affinity_str:>20}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_sistema(stdscr, datos, alto, ancho):
    stdscr.addstr(2, 0, "ESTADO DEL SISTEMA", curses.A_BOLD)

    # si todavia no hay datos, no dibujamos nada
    if not datos:
        stdscr.addstr(4, 0, "(esperando datos...)")
        return

    # --- uptime: convertir segundos a h/m/s ---
    seg = datos["uptime_segundos"]
    h = seg // 3600
    m = (seg % 3600) // 60
    s = seg % 60

    # --- memoria: pasar de kB a MB para que sea legible ---
    # los valores vienen como '3392028 kB' (string), sacamos el numero
    total_mb = int(datos["mem_total"].split()[0]) // 1024
    disp_mb = int(datos["mem_disponible"].split()[0]) // 1024
    usada_mb = total_mb - disp_mb

    # --- dibujar, linea por linea, con etiquetas legibles ---
    lineas = [
        f"Uptime         : {h}h {m}m {s}s",
        f"RAM total      : {total_mb} MB",
        f"RAM usada      : {usada_mb} MB",
        f"RAM disponible : {disp_mb} MB",
        f"Load promedio  : {datos['load_1min']} (1m)  "
        f"{datos['load_5min']} (5m)  {datos['load_15min']} (15m)",
    ]

    fila = 4
    for linea in lineas:
        if fila >= alto - 1:
            break
        stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_detalle(stdscr, shared, pin_pid, fila_sep, alto, ancho):
    """Panel de detalle del proceso pineado, desde fila_sep hacia abajo.
    Junta info del PID desde varias vistas del shared (NO toca /proc)."""

    # linea separadora
    stdscr.addstr(fila_sep, 0, "-" * (ancho - 1))

    # sacar la ficha del PID pineado de cada vista (o None si no esta)
    r = shared.get("resumen", {}).get(pin_pid)
    m = shared.get("memoria", {}).get(pin_pid)
    s = shared.get("scheduling", {}).get(pin_pid)

    if r is None:
        stdscr.addstr(fila_sep + 1, 0,
                      f"PID {pin_pid} - proceso no disponible (murio)")
        return

    stdscr.addstr(fila_sep + 1, 0,
                  f"DETALLE - PID {pin_pid}: {r.get('comm','?')}", curses.A_BOLD)

    lineas = []
    lineas.append(f"Estado: {r.get('estado','?')}   "
                  f"CPU: {r.get('cpu',0):.1f}%   "
                  f"Threads: {r.get('Threads','?')}   "
                  f"PPID: {r.get('PPid','?')}")
    if m is not None:
        lineas.append(f"VmRSS: {m.get('VmRSS','?')}   "
                      f"VmSize: {m.get('VmSize','?')}   "
                      f"minflt: {m.get('minflt','?')}   "
                      f"majflt: {m.get('majflt','?')}")
    if s is not None:
        lineas.append(f"Nice: {s.get('nice','?')}   "
                      f"Prio: {s.get('priority','?')}   "
                      f"Policy: {s.get('policy','?')}   "
                      f"ctxt vol/nonvol: {s.get('voluntary_ctxt_switches','?')}/"
                      f"{s.get('nonvoluntary_ctxt_switches','?')}")

    fila = fila_sep + 2
    for linea in lineas:
        if fila >= alto - 1:
            break
        stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_placeholder(stdscr, datos, alto, ancho, nombre):
    stdscr.addstr(3, 0, f"Vista '{nombre}' - en construccion")
    stdscr.addstr(5, 0, f"(datos disponibles: {len(datos)} procesos)")

# ---------------------------------------------------------------------------
# Mapa: tecla -> (nombre de vista, clave en el shared)
# ---------------------------------------------------------------------------
VISTAS = {
    ord('1'): ("RESUMEN",    "resumen"),
    ord('2'): ("MEMORIA",    "memoria"),
    ord('3'): ("SENALES",    "senales"),
    ord('4'): ("FDS",        "fds"),
    ord('5'): ("THREADS",    "threads"),
    ord('6'): ("SCHEDULING", "scheduling"),
    ord('7'): ("SISTEMA",    "sistema"),
}


def _loop(stdscr, shared):
    curses.curs_set(0)
    stdscr.timeout(200)
    stdscr.keypad(True)

    vista_nombre = "RESUMEN"
    vista_clave = "resumen"
    seleccion = 0
    offset = 0
    pin_pid = None

    while shared["seguir"]:
        stdscr.erase()
        alto, ancho = stdscr.getmaxyx()

        titulo = f"MONITOR DE PROCESOS - Vista: {vista_nombre}"
        stdscr.addstr(0, 0, titulo[:ancho - 1], curses.A_BOLD)

        datos = shared.get(vista_clave, {})
        # ordenar UNA vez, fuente unica
        if vista_clave != "sistema":
            procesos = ordenar_vista(vista_clave, datos)
        else:
            procesos = []
        cantidad = len(datos)

        # --- limitar seleccion al rango valido ---
        if seleccion < 0:
            seleccion = 0
        if cantidad > 0 and seleccion >= cantidad:
            seleccion = cantidad - 1

        # si hay pin, la lista usa la mitad de arriba; el detalle va abajo
        if pin_pid is not None:
            fila_sep = alto // 2
            filas_visibles = fila_sep - 3        # menos el header (filas 0-2)
        else:
            fila_sep = None
            filas_visibles = alto - 4

        if seleccion < offset:                      # se fue por arriba
            offset = seleccion
        if seleccion >= offset + filas_visibles:    # se fue por abajo
            offset = seleccion - filas_visibles + 1
        

        if vista_clave == "resumen":
            dibujar_resumen(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles)
        elif vista_clave == "memoria":
            dibujar_memoria(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles)
        elif vista_clave == "senales":
            dibujar_senales(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles)
        elif vista_clave == "fds":
            dibujar_fds(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles)
        elif vista_clave == "threads":
            dibujar_threads(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles)
        elif vista_clave == "scheduling":
            dibujar_scheduling(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles)
        elif vista_clave == "sistema":
            dibujar_sistema(stdscr, datos, alto, ancho)
        else:
            dibujar_placeholder(stdscr, datos, alto, ancho, vista_nombre)
        
        # panel de detalle abajo (si hay algo pineado y no es la vista sistema)
        if pin_pid is not None and vista_clave != "sistema":
            dibujar_detalle(stdscr, shared, pin_pid, fila_sep, alto, ancho)

        pie = "1-7: vista | flechas: navegar | Enter: pin | q: salir"

        stdscr.addstr(alto - 1, 0, pie[:ancho - 1], curses.A_DIM)

        stdscr.refresh()

        tecla = stdscr.getch()
        if tecla == ord('q'):
            break
        elif tecla == curses.KEY_UP:
            seleccion -= 1
        elif tecla == curses.KEY_DOWN:
            seleccion += 1
        elif tecla in VISTAS:
            vista_nombre, vista_clave = VISTAS[tecla]
            seleccion = 0
            offset = 0                  # al cambiar de vista, resetear scroll
        elif tecla == ord('\n') or tecla == curses.KEY_ENTER:
            if pin_pid is not None:
                pin_pid = None                       # ya habia pin -> despinear
            elif 0 <= seleccion < len(procesos):
                pin_pid = procesos[seleccion][0]     # pinear el seleccionado

def display(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    curses.wrapper(_loop, shared)
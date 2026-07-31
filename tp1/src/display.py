import curses
import signal


# ---------------------------------------------------------------------------
# Funciones de dibujo: una por vista. Cada una recibe la pantalla, los datos
# de esa vista (leidos del shared) y las dimensiones, y dibuja su tabla.
# ---------------------------------------------------------------------------

def dibujar_resumen(stdscr, datos, alto, ancho):
    header = f"{'PID':>7} {'CPU%':>6} {'THR':>4} {'ST':>3}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    procesos = sorted(datos.items(), key=lambda x: x[1]['cpu'], reverse=True)

    fila = 3
    for pid, info in procesos:
        if fila >= alto - 1:
            break
        linea = (f"{pid:>7} {info['cpu']:>6.1f} "
                 f"{info['Threads']:>4} {info['estado']:>3}  {info['comm']}")
        stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_memoria(stdscr, datos, alto, ancho):
    header = f"{'PID':>7} {'VmRSS':>12} {'VmSize':>12} {'minflt':>10} {'majflt':>8}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    # ordenar por VmRSS (ojo: es string tipo '1804 kB', hay que convertir)
    procesos = sorted(datos.items(),
                      key=lambda x: int(x[1]['VmRSS'].split()[0]),
                      reverse=True)

    fila = 3
    for pid, info in procesos:
        if fila >= alto - 1:
            break
        linea = (f"{pid:>7} {info['VmRSS']:>12} {info['VmSize']:>12} "
                 f"{info['minflt']:>10} {info['majflt']:>8}  {info['comm']}")
        stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_senales(stdscr, datos, alto, ancho):
    header = f"{'PID':>7} {'SigBlk':>10} {'SigIgn':>10} {'SigCgt':>10} {'SigPnd':>10}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    procesos = sorted(datos.items(), key=lambda x: len(x[1]['SigCgt']), reverse=True)

    fila = 3
    for pid, info in procesos:
        if fila >= alto - 1:
            break
        linea = (f"{pid:>7} {len(info['SigBlk']):>10} {len(info['SigIgn']):>10} "
                 f"{len(info['SigCgt']):>10} {len(info['SigPnd']):>10}  {info['comm']}")
        stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_fds(stdscr, datos, alto, ancho):
    header = f"{'PID':>7} {'#FDs':>5} {'Tipos de FDs'}"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    procesos = sorted(datos.items(), key=lambda x: int(x[0]))  # ordenar por PID

    fila = 3
    for pid, info in procesos:
        if fila >= alto - 1:
            break
        tipos = {}
        for fd_data in info.values():
            tipo = fd_data['tipo']
            tipos[tipo] = tipos.get(tipo, 0) + 1 # contar cuántos de cada tipo
        tipos_str = ", ".join(f"{k}:{v}" for k, v in tipos.items()) # crear string de tipos
        linea = f"{pid:>7} {len(info):>5} {tipos_str}"
        stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_threads(stdscr, datos, alto, ancho):
    header = f"{'PID':>7} {'#THR':>5} {'maxCPU':>7}  THREADS (tid:nombre:cpu%)"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    def max_cpu(info):
        # el CPU% del thread más activo de este proceso (0 si no tiene threads)
        if not info['threads']:
            return 0.0
        return max(d['cpu'] for d in info['threads'].values())

    procesos = sorted(datos.items(), key=lambda x: max_cpu(x[1]), reverse=True)

    fila = 3
    for pid, info in procesos:
        if fila >= alto - 1:
            break
        muestra = list(info['threads'].items())[:4] # mostrar solo los primeros 4 threads
        threads_str = ", ".join(f"{tid}:{d['comm']}:{d['cpu']:.1f}" for tid, d in muestra)
        linea = f"{pid:>7} {info['num_threads']:>5} {max_cpu(info):>7.1f}  {threads_str}"
        stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_scheduling(stdscr, datos, alto, ancho):
    header = f"{'PID':>7} {'PRIO':>5} {'NICE':>5} {'POLICY':>10} {'VOLUNTARY':>10} {'NONVOLUNTARY':>15} {'PGID':>7} {'SID':>7} {'AFFINITY':>20}"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    proceos = sorted(datos.items(), key=lambda x: (int(x[1]['priority']), int(x[1]['nice'])), reverse=True)

    fila = 3
    for pid, info in proceos:
        if fila >= alto - 1:
            break
        affinity_str = str(info['affinity'])
        linea = (f"{pid:>7} {info['priority']:>5} {info['nice']:>5} "
                 f"{info['policy']:>10} {info['voluntary_ctxt_switches']:>10} "
                 f"{info['nonvoluntary_ctxt_switches']:>15} {info['pgid']:>7} "
                 f"{info['sid']:>7} {affinity_str:>20}")
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

    vista_nombre = "RESUMEN"      # vista activa (empieza en resumen)
    vista_clave = "resumen"

    while shared["seguir"]:
        stdscr.erase()
        alto, ancho = stdscr.getmaxyx()

        # --- encabezado con la vista activa ---
        titulo = f"MONITOR DE PROCESOS - Vista: {vista_nombre}"
        stdscr.addstr(0, 0, titulo[:ancho - 1], curses.A_BOLD)

        # --- leer datos de la vista activa y dibujar ---
        datos = shared.get(vista_clave, {})

        if vista_clave == "resumen":
            dibujar_resumen(stdscr, datos, alto, ancho)
        elif vista_clave == "memoria":
            dibujar_memoria(stdscr, datos, alto, ancho)
        elif vista_clave == "senales":
            dibujar_senales(stdscr, datos, alto, ancho)
        elif vista_clave == "fds":
            dibujar_fds(stdscr, datos, alto, ancho)
        elif vista_clave == "threads":
            dibujar_threads(stdscr, datos, alto, ancho)
        elif vista_clave == "scheduling":
            dibujar_scheduling(stdscr, datos, alto, ancho)
        elif vista_clave == "sistema":
            dibujar_sistema(stdscr, datos, alto, ancho)
        else:
            dibujar_placeholder(stdscr, datos, alto, ancho, vista_nombre)

        # --- pie ---
        pie = "1-7: cambiar vista  |  q: salir"
        stdscr.addstr(alto - 1, 0, pie[:ancho - 1], curses.A_DIM)

        stdscr.refresh()

        # --- teclado ---
        tecla = stdscr.getch()
        if tecla == ord('q'):
            break
        elif tecla in VISTAS:
            vista_nombre, vista_clave = VISTAS[tecla]


def display(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    curses.wrapper(_loop, shared)
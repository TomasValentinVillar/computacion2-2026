import curses
import signal


# ---------------------------------------------------------------------------
# Funciones de dibujo: una por vista. Cada una recibe la pantalla, los datos
# de esa vista (leidos del shared) y las dimensiones, y dibuja su tabla.
# ---------------------------------------------------------------------------

def orden_natural(vista_clave, items):
    """El orden 'propio' de cada vista, para usar de fallback."""
    if vista_clave == "resumen":
        return sorted(items, key=lambda x: x[1].get('cpu', 0), reverse=True)
    elif vista_clave == "memoria":
        return sorted(items, key=lambda x: _rss(x[1]), reverse=True)
    elif vista_clave == "senales":
        return sorted(items, key=lambda x: len(x[1].get('SigCgt', [])), reverse=True)
    elif vista_clave == "fds":
        return sorted(items, key=lambda x: len(x[1]))   # cantidad de fds
    elif vista_clave == "threads":
        return sorted(items, key=lambda x: _maxcpu(x[1]), reverse=True)
    elif vista_clave == "scheduling":
        return sorted(items,
                      key=lambda x: (int(x[1].get('priority', 0)),
                                     int(x[1].get('nice', 0))),
                      reverse=True)
    else:
        return items


def _rss(info):
    v = info.get('VmRSS', '')
    return int(v.split()[0]) if v else 0


def _maxcpu(info):
    if info.get('threads'):
        return max(d['cpu'] for d in info['threads'].values())
    return 0


def _tiene_cpu(vista_clave):
    return vista_clave in ("resumen", "threads")


def _tiene_rss(vista_clave):
    return vista_clave == "memoria"


def ordenar_vista(vista_clave, datos, orden):
    items = list(datos.items())

    if orden == "pid":
        return sorted(items, key=lambda x: int(x[0]))

    elif orden == "cpu":
        if _tiene_cpu(vista_clave):
            # resumen -> por cpu ; threads -> por maxCPU
            if vista_clave == "threads":
                return sorted(items, key=lambda x: _maxcpu(x[1]), reverse=True)
            return sorted(items, key=lambda x: x[1].get('cpu', 0), reverse=True)
        else:
            return orden_natural(vista_clave, items)   # fallback

    elif orden == "rss":
        if _tiene_rss(vista_clave):
            return sorted(items, key=lambda x: _rss(x[1]), reverse=True)
        else:
            return orden_natural(vista_clave, items)   # fallback

    else:
        return orden_natural(vista_clave, items)
# --- dibujar_resumen: ahora recibe offset y dibuja solo la tajada visible ---

def dibujar_resumen(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose):
    if verbose:
        header = f"{'PID':>7} {'UID':>6} {'PPID':>7} {'CPU%':>6} {'THR':>4} {'ST':>3}  COMANDO"
    else:
        header = f"{'PID':>7} {'UID':>6} {'CPU%':>6} {'THR':>4} {'ST':>3}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    visibles = procesos[offset : offset + filas_visibles]
    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        uid = info.get('Uid', '').split()[0] if info.get('Uid') else '?'
        if verbose:
            linea = (f"{pid:>7} {uid:>6} {info['PPid']:>7} {info['cpu']:>6.1f} "
                     f"{info['Threads']:>4} {info['estado']:>3}  {info['comm']}")
        else:
            linea = (f"{pid:>7} {uid:>6} {info['cpu']:>6.1f} "
                     f"{info['Threads']:>4} {info['estado']:>3}  {info['comm']}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1


def dibujar_memoria(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose):
    if verbose:
        header = f"{'PID':>7} {'VmRSS':>12} {'VmSize':>12} {'VmHWM':>12} {'VmSwap':>10} {'minflt':>10} {'majflt':>8}  COMANDO"
    else:
        header = f"{'PID':>7} {'VmRSS':>12} {'VmSize':>12} {'minflt':>10} {'majflt':>8}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    visibles = procesos[offset : offset + filas_visibles]
    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        if verbose:
            linea = (f"{pid:>7} {info['VmRSS']:>12} {info['VmSize']:>12} "
                     f"{info.get('VmHWM','?'):>12} {info.get('VmSwap','?'):>10} "
                     f"{info['minflt']:>10} {info['majflt']:>8}  {info['comm']}")
        else:
            linea = (f"{pid:>7} {info['VmRSS']:>12} {info['VmSize']:>12} "
                     f"{info['minflt']:>10} {info['majflt']:>8}  {info['comm']}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_senales(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose):
    if verbose:
        header = f"{'PID':>7} {'#Blk':>5} {'#Ign':>5} {'#Cgt':>5} {'#Pnd':>5} {'#ShdPnd':>8}  COMANDO / SigCgt"
    else:
        header = f"{'PID':>7} {'SigBlk':>10} {'SigIgn':>10} {'SigCgt':>10} {'SigPnd':>10}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    visibles = procesos[offset : offset + filas_visibles]
    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        if verbose:
            # nombres de las primeras señales con handler
            cgt_nombres = ", ".join(info.get('SigCgt', [])[:6])
            linea = (f"{pid:>7} {len(info['SigBlk']):>5} {len(info['SigIgn']):>5} "
                     f"{len(info['SigCgt']):>5} {len(info['SigPnd']):>5} "
                     f"{len(info.get('ShdPnd', [])):>8}  {info['comm']}: {cgt_nombres}")
        else:
            linea = (f"{pid:>7} {len(info['SigBlk']):>10} {len(info['SigIgn']):>10} "
                     f"{len(info['SigCgt']):>10} {len(info['SigPnd']):>10}  {info['comm']}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_fds(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose):
    header = f"{'PID':>7} {'#FDs':>5}  " + ("FDs (fd -> destino)" if verbose else "Tipos de FDs")
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    visibles = procesos[offset : offset + filas_visibles]
    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        if verbose:
            # mostrar los primeros FDs con su destino
            fds_muestra = list(info.items())[:5]
            fds_str = ", ".join(f"{fd}->{d['destino']}" for fd, d in fds_muestra)
            linea = f"{pid:>7} {len(info):>5}  {fds_str}"
        else:
            tipos = {}
            for fd_data in info.values():
                tipo = fd_data['tipo']
                tipos[tipo] = tipos.get(tipo, 0) + 1
            tipos_str = ", ".join(f"{k}:{v}" for k, v in tipos.items())
            linea = f"{pid:>7} {len(info):>5}  {tipos_str}"
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_threads(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose):
    if verbose:
        header = f"{'PID':>7} {'#THR':>5} {'maxCPU':>7} {'vol':>8} {'nonvol':>8}  THREADS (tid:nombre:estado:cpu%)"
    else:
        header = f"{'PID':>7} {'#THR':>5} {'maxCPU':>7}  THREADS (tid:nombre:cpu%)"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    def max_cpu(info):
        if not info['threads']:
            return 0.0
        return max(d['cpu'] for d in info['threads'].values())

    visibles = procesos[offset : offset + filas_visibles]
    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i

        muestra = list(info['threads'].items())[:4]

        if verbose:
            threads_str = ", ".join(
                f"{tid}:{d['comm']}:{d['estado']}:{d['cpu']:.1f}" for tid, d in muestra)
        else:
            threads_str = ", ".join(
                f"{tid}:{d['comm']}:{d['cpu']:.1f}" for tid, d in muestra)

        if verbose:
            th_principal = info['threads'].get(pid, {})
            vol = th_principal.get('voluntary', '?')
            nonvol = th_principal.get('nonvoluntary', '?')
            linea = (f"{pid:>7} {info['num_threads']:>5} {max_cpu(info):>7.1f} "
                     f"{vol:>8} {nonvol:>8}  {threads_str}")
        else:
            linea = (f"{pid:>7} {info['num_threads']:>5} {max_cpu(info):>7.1f}  {threads_str}")

        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_scheduling(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose):
    if verbose:
        header = f"{'PID':>7} {'PRIO':>5} {'NICE':>5} {'RT':>3} {'POLICY':>8} {'utime':>8} {'stime':>8} {'vol':>8} {'nonvol':>8}  COMANDO"
    else:
        header = f"{'PID':>7} {'PRIO':>5} {'NICE':>5} {'POLICY':>10} {'VOLUNTARY':>10} {'NONVOLUNTARY':>13} {'PGID':>7} {'SID':>7}  COMANDO"
    stdscr.addstr(2, 0, header, curses.A_BOLD)

    visibles = procesos[offset : offset + filas_visibles]
    fila = 3
    for i, (pid, info) in enumerate(visibles):
        indice_real = offset + i
        if verbose:
            linea = (f"{pid:>7} {info['priority']:>5} {info['nice']:>5} "
                     f"{info.get('rt_priority','?'):>3} {info['policy']:>8} "
                     f"{info.get('utime','?'):>8} {info.get('stime','?'):>8} "
                     f"{info['voluntary_ctxt_switches']:>8} {info['nonvoluntary_ctxt_switches']:>8}  {info['comm']}")
        else:
            linea = (f"{pid:>7} {info['priority']:>5} {info['nice']:>5} "
                     f"{info['policy']:>10} {info['voluntary_ctxt_switches']:>10} "
                     f"{info['nonvoluntary_ctxt_switches']:>13} {info['pgid']:>7} {info['sid']:>7}  {info['comm']}")
        if indice_real == seleccion:
            stdscr.addstr(fila, 0, linea[:ancho - 1], curses.A_REVERSE)
        else:
            stdscr.addstr(fila, 0, linea[:ancho - 1])
        fila += 1

def dibujar_sistema(stdscr, datos, alto, ancho, verbose):
    stdscr.addstr(2, 0, "ESTADO DEL SISTEMA", curses.A_BOLD)

    if not datos:
        stdscr.addstr(4, 0, "(esperando datos...)")
        return

    # --- uptime a h/m/s ---
    seg = datos["uptime_segundos"]
    h = seg // 3600
    m = (seg % 3600) // 60
    s = seg % 60

    # --- memoria a MB ---
    def a_mb(campo):
        v = datos.get(campo, "0 kB")
        return int(v.split()[0]) // 1024 if v else 0

    total_mb = a_mb("mem_total")
    disp_mb = a_mb("mem_disponible")
    usada_mb = total_mb - disp_mb

    lineas = [
        f"Uptime         : {h}h {m}m {s}s",
        f"RAM total      : {total_mb} MB",
        f"RAM usada      : {usada_mb} MB",
        f"RAM disponible : {disp_mb} MB",
        f"Load promedio  : {datos['load_1min']} (1m)  "
        f"{datos['load_5min']} (5m)  {datos['load_15min']} (15m)",
        f"Procesos       : {datos.get('procesos_total','?')}   "
        f"Threads: {datos.get('threads_total','?')}   "
        f"Zombies: {datos.get('zombies','?')}",
    ]

    # --- lo extra solo en verbose ---
    if verbose:
        # memoria detallada
        lineas.append("")
        lineas.append(f"Buffers        : {a_mb('mem_buffers')} MB   "
                      f"Cached: {a_mb('mem_cached')} MB")
        lineas.append(f"Swap total     : {a_mb('swap_total')} MB   "
                      f"Swap libre: {a_mb('swap_free')} MB")

        # CPU global
        lineas.append("")
        lineas.append(f"CPU global     : user {datos.get('cpu_user','?')}%   "
                      f"system {datos.get('cpu_system','?')}%   "
                      f"idle {datos.get('cpu_idle','?')}%   "
                      f"iowait {datos.get('cpu_iowait','?')}%")

        # procesos por estado
        por_estado = datos.get('procesos_por_estado', {})
        estados_str = "   ".join(f"{k}: {v}" for k, v in por_estado.items())
        lineas.append(f"Por estado     : {estados_str}")

        # boot time
        import time as _t
        bt = datos.get('boot_time')
        if bt:
            bt_str = _t.strftime("%Y-%m-%d %H:%M:%S", _t.localtime(bt))
            lineas.append(f"Boot time      : {bt_str}")

        # top 3 CPU
        lineas.append("")
        lineas.append("Top 3 CPU:")
        for pid, comm, cpu in datos.get('top_cpu', []):
            lineas.append(f"   {pid:>7}  {comm:<20} {cpu:.1f}%")

        # top 3 memoria
        lineas.append("Top 3 memoria:")
        for pid, comm, rss in datos.get('top_mem', []):
            lineas.append(f"   {pid:>7}  {comm:<20} {rss}")

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


def _loop(stdscr, shared, intervalos):
    curses.curs_set(0)
    stdscr.timeout(200)
    stdscr.keypad(True)

    vista_nombre = "RESUMEN"
    vista_clave = "resumen"
    seleccion = 0
    offset = 0
    pin_pid = None
    filtro = ""
    modo_busqueda = False
    tipo_filtro = None
    orden = "cpu"

    while shared["seguir"]:
        stdscr.erase()
        alto, ancho = stdscr.getmaxyx()

        titulo = f"MONITOR DE PROCESOS - Vista: {vista_nombre}  [orden: {orden}]  [cada {intervalos[vista_clave].value}s]"
        verbose = shared.get("verbose", False)
        if verbose:
            titulo += "  [VERBOSE]"
        stdscr.addstr(0, 0, titulo[:ancho - 1], curses.A_BOLD)

        datos = shared.get(vista_clave, {})
        # ordenar UNA vez, fuente unica
        if vista_clave != "sistema":
            procesos = ordenar_vista(vista_clave, datos, orden)
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
        
        datos = shared.get(vista_clave, {})

        if vista_clave != "sistema":
            procesos = ordenar_vista(vista_clave, datos, orden)
        else:
            procesos = []

        # --- aplicar filtro por nombre ---
        if filtro:
            if tipo_filtro == "nombre":
                procesos = [(pid, info) for pid, info in procesos
                            if filtro.lower() in info.get('comm', '').lower()]
            elif tipo_filtro == "usuario":
                procesos = [(pid, info) for pid, info in procesos
                    if info.get('Uid') and filtro == info['Uid'].split()[0]]

        cantidad = len(procesos)
        # ... el resto (limitar seleccion, offset, etc.) sigue igual ...

        if vista_clave == "resumen":
            dibujar_resumen(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose)
        elif vista_clave == "memoria":
            dibujar_memoria(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose)
        elif vista_clave == "senales":
            dibujar_senales(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose)
        elif vista_clave == "fds":
            dibujar_fds(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose)
        elif vista_clave == "threads":
            dibujar_threads(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose)
        elif vista_clave == "scheduling":
            dibujar_scheduling(stdscr, procesos, alto, ancho, seleccion, offset, filas_visibles, verbose)
        elif vista_clave == "sistema":
            dibujar_sistema(stdscr, datos, alto, ancho, verbose)
        else:
            dibujar_placeholder(stdscr, datos, alto, ancho, vista_nombre)
        
        # panel de detalle abajo (si hay algo pineado y no es la vista sistema)
        if pin_pid is not None and vista_clave != "sistema":
            dibujar_detalle(stdscr, shared, pin_pid, fila_sep, alto, ancho)
        
        if modo_busqueda:
            etiqueta = "Buscar nombre" if tipo_filtro == "nombre" else "Buscar UID"
            stdscr.addstr(alto - 2, 0, f"{etiqueta}: {filtro}_"[:ancho - 1])
        elif filtro:
            stdscr.addstr(alto - 2, 0,
                          f"Filtro {tipo_filtro}: '{filtro}' (ESC limpia)"[:ancho - 1],
                          curses.A_DIM)
        pie = "1-7:vista | flechas | Enter:pin | /:nombre | u:usuario | c:orden | +/-:intervalo | q:salir"

        stdscr.addstr(alto - 1, 0, pie[:ancho - 1], curses.A_DIM)

        stdscr.refresh()

        tecla = stdscr.getch()

        if modo_busqueda:
            # --- MODO BUSQUEDA: acumular caracteres ---
            if tecla == ord('\n') or tecla == curses.KEY_ENTER:
                modo_busqueda = False               # confirmar
            elif tecla == 27:                        # ESC: cancelar y limpiar
                modo_busqueda = False
                filtro = ""
            elif tecla == curses.KEY_BACKSPACE or tecla == 127:
                filtro = filtro[:-1]                 # borrar ultimo caracter
            elif 32 <= tecla <= 126:
                filtro += chr(tecla)                 # agregar caracter
            # al cambiar el filtro, reseteamos la seleccion
            seleccion = 0
            offset = 0
        else:
            # --- MODO NORMAL: las teclas de siempre ---
            if tecla == ord('q'):
                break
            elif tecla == ord('/'):
                modo_busqueda = True
                tipo_filtro = "nombre"
                filtro = ""                          # empezar filtro limpio
                seleccion = 0
                offset = 0
            elif tecla == ord('u'):
                modo_busqueda = True
                tipo_filtro = "usuario"
                filtro = ""
                seleccion = 0
                offset = 0
            elif tecla == ord('c'):
                if orden == "cpu":
                    orden = "rss"
                elif orden == "rss":
                    orden = "pid"
                else:
                    orden = "cpu"
                seleccion = 0
                offset = 0
            elif tecla == ord('+') or tecla == ord('='):    # '=' porque + suele ser shift+=
                intervalos[vista_clave].value += 1
            elif tecla == ord('-'):
                if intervalos[vista_clave].value > 1:        # no bajar de 1 segundo
                    intervalos[vista_clave].value -= 1
            elif tecla == 27:                        # ESC en modo normal: limpiar filtro
                filtro = ""
                seleccion = 0
                offset = 0
            elif tecla == curses.KEY_UP:
                seleccion -= 1
            elif tecla == curses.KEY_DOWN:
                seleccion += 1
            elif tecla == ord('\n') or tecla == curses.KEY_ENTER:
                if pin_pid is not None:
                    pin_pid = None
                elif 0 <= seleccion < len(procesos):
                    pin_pid = procesos[seleccion][0]
            elif tecla in VISTAS:
                vista_nombre, vista_clave = VISTAS[tecla]
                seleccion = 0
                offset = 0

def display(shared, intervalos):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)
    signal.signal(signal.SIGUSR1, signal.SIG_IGN)
    signal.signal(signal.SIGUSR2, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    curses.wrapper(_loop, shared, intervalos)
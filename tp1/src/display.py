import curses
import signal


def _loop(stdscr, shared):
    curses.curs_set(0)
    stdscr.timeout(200)         # refresca cada 200ms si no hay tecla

    while shared["seguir"]:
        stdscr.erase()

        # alto y ancho actuales de la terminal
        alto, ancho = stdscr.getmaxyx()

        # --- leer datos del analizador de resumen ---
        datos = shared.get("resumen", {})   # {} si todavia no publico nada

        # --- encabezado ---
        stdscr.addstr(0, 0, "MONITOR DE PROCESOS - Vista: RESUMEN", curses.A_BOLD)
        header = f"{'PID':>7} {'CPU%':>6} {'THR':>4} {'ST':>3}  COMANDO"
        stdscr.addstr(2, 0, header, curses.A_BOLD)

        # --- filas de procesos ---
        # ordenar por CPU% descendente
        procesos = sorted(datos.items(),
                          key=lambda x: x[1]['cpu'],
                          reverse=True)

        fila = 3
        for pid, info in procesos:
            # cortar si nos quedamos sin pantalla (dejamos 1 linea de margen abajo)
            if fila >= alto - 1:
                break
            linea = (f"{pid:>7} {info['cpu']:>6.1f} "
                     f"{info['Threads']:>4} {info['estado']:>3}  {info['comm']}")
            # recortar la linea si es mas ancha que la terminal (evita crash)
            stdscr.addstr(fila, 0, linea[:ancho - 1])
            fila += 1

        # --- pie ---
        stdscr.addstr(alto - 1, 0, "q: salir", curses.A_DIM)

        stdscr.refresh()

        tecla = stdscr.getch()
        if tecla == ord('q'):
            break


def display(shared):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    curses.wrapper(_loop, shared)
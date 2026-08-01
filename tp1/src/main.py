import signal
import time
import json
from multiprocessing import Process, Manager, Value

from analizadores.resumen import analizador_resumen
from analizadores.memoria import analizador_memoria
from analizadores.señales import analizador_senales
from analizadores.fds import analizador_fds
from analizadores.threads import analizador_threads
from analizadores.scheduling import analizador_scheduling
from analizadores.sistema import analizador_sistema
from display import display


# ---------------------------------------------------------------------------
# Banderas: los handlers SOLO las levantan (patron flag, async-signal-safe).
# El loop principal las revisa y hace el trabajo real en un punto seguro.
# ---------------------------------------------------------------------------
cerrar = False
recargar = False          # SIGHUP  -> recargar config
dump = False              # SIGUSR1 -> dump a json
toggle_verbose = False    # SIGUSR2 -> toggle verbose


def manejador(signum, frame):
    global cerrar
    cerrar = True


def manejador_hup(signum, frame):
    global recargar
    recargar = True


def manejador_usr1(signum, frame):
    global dump
    dump = True


def manejador_usr2(signum, frame):
    global toggle_verbose
    toggle_verbose = True


def dump_snapshot(shared):
    """Guarda una foto de todos los datos actuales a dump_<timestamp>.json."""
    timestamp = int(time.time())
    nombre = f"dump_{timestamp}.json"
    snapshot = {}
    for clave in ["resumen", "memoria", "senales", "fds",
                  "threads", "scheduling", "sistema"]:
        snapshot[clave] = dict(shared.get(clave, {}))
    with open(nombre, "w") as f:
        json.dump(snapshot, f, indent=2)


if __name__ == "__main__":
    # registrar los handlers
    signal.signal(signal.SIGINT, manejador)
    signal.signal(signal.SIGTERM, manejador)
    signal.signal(signal.SIGHUP, manejador_hup)
    signal.signal(signal.SIGUSR1, manejador_usr1)
    signal.signal(signal.SIGUSR2, manejador_usr2)

    manager = Manager()
    shared = manager.dict()
    shared["seguir"] = True
    shared["verbose"] = False

    intervalos = {
        "resumen": Value('i', 2),
        "memoria": Value('i', 3),
        "fds": Value('i', 5),
        "threads": Value('i', 2),
        "senales": Value('i', 10),
        "scheduling": Value('i', 10),
        "sistema": Value('i', 2),
    }

    # lista de procesos (escalable)
    procesos = [
        Process(target=analizador_resumen, args=(shared, intervalos["resumen"])),
        Process(target=analizador_memoria, args=(shared, intervalos["memoria"])),
        Process(target=analizador_senales, args=(shared, intervalos["senales"])),
        Process(target=analizador_fds, args=(shared, intervalos["fds"])),
        Process(target=analizador_threads, args=(shared, intervalos["threads"])),
        Process(target=analizador_scheduling, args=(shared, intervalos["scheduling"])),
        Process(target=analizador_sistema, args=(shared, intervalos["sistema"])),
        Process(target=display, args=(shared, intervalos)),
    ]

    # lanzar TODOS
    for p in procesos:
        p.start()

    # --- loop principal del padre ---
    while not cerrar:
        time.sleep(0.5)

        # SIGUSR2: toggle verbose
        if toggle_verbose:
            toggle_verbose = False
            shared["verbose"] = not shared["verbose"]

        # SIGUSR1: dump del snapshot
        if dump:
            dump = False
            dump_snapshot(shared)

        # SIGHUP: recargar config (lo implementamos cuando exista config.json)
        if recargar:
            recargar = False
            # recargar_config(shared, intervalos)   # TODO: cuando haya config.json
            pass

    # cierre ordenado
    print("\ncerrando...")
    shared["seguir"] = False
    for p in procesos:
        p.join()
    print("cerrado limpio")
"""Estado compartido en memoria entre los endpoints y los workers.

Un proceso y un hilo: alcanza con dicts comunes, sin Manager ni Lock.
"""
import asyncio

# id -> datos de la tarea. Vive desde el POST para siempre (el GET la consulta).
tareas: dict[int, dict] = {}

# id -> asyncio.Task que la está ejecutando. Solo mientras se ejecuta:
# es lo que necesita el DELETE para llamar a .cancel().
en_ejecucion: dict[int, asyncio.Task] = {}

# True desde que llega SIGTERM/SIGINT: el POST deja de aceptar tareas (503).
apagando = False

_ultimo_id = 0


def nuevo_id() -> int:
    """Devuelve el próximo id: 1, 2, 3...

    Sin Lock: no hay ningún await adentro, así que el event loop no puede
    meter otra corrutina entre el incremento y el return.
    """
    global _ultimo_id
    _ultimo_id += 1
    return _ultimo_id

"""Volcado del estado a JSON al apagar, y reporte del volcado previo al arrancar."""
import glob
import json
import logging
import os
import time
from collections import Counter

log = logging.getLogger('uvicorn.error')   # mismo canal que los logs de uvicorn

# En Docker es un volumen (./datos del host montado en /app/datos): así el JSON
# sobrevive a `docker compose down`. Fuera de Docker, tp2/datos/.
DIR_ESTADO = os.environ.get('DIR_ESTADO', os.path.join(os.path.dirname(__file__), '..', 'datos'))


def volcar(tareas: dict[int, dict]) -> str:
    """Escribe estado_<timestamp>.json con todas las tareas. Devuelve la ruta."""
    os.makedirs(DIR_ESTADO, exist_ok=True)
    ruta = os.path.join(DIR_ESTADO, f"estado_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(ruta, 'w') as f:
        json.dump({'volcado': time.time(), 'tareas': list(tareas.values())}, f, indent=2)
    return ruta


def reportar_volcado_previo():
    """Si hay un volcado anterior, lo reporta por log (no reanuda nada)."""
    volcados = sorted(glob.glob(os.path.join(DIR_ESTADO, 'estado_*.json')))
    if not volcados:
        log.info('sin volcado previo')
        return
    ultimo = volcados[-1]
    try:
        with open(ultimo) as f:
            tareas = json.load(f)['tareas']
    except (OSError, ValueError, KeyError) as e:
        log.warning(f'volcado previo ilegible ({ultimo}): {e}')
        return
    por_estado = dict(Counter(t['estado'] for t in tareas))
    log.info(f'volcado previo: {os.path.basename(ultimo)} '
             f'({len(tareas)} tareas: {por_estado})')

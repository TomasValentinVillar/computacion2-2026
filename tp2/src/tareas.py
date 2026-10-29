"""Las funciones que hacen el trabajo de cada tipo: descargar, hashear, esperar."""
import asyncio
import hashlib
import time

import httpx

TIMEOUT_POR_URL = 10   # una URL colgada no debería arrastrar a las demás


def hashear(texto: str, iteraciones: int) -> str:
    """CPU-bound puro: SHA-256 aplicado `iteraciones` veces.

    Función común (no async) y a nivel de módulo, a propósito:
    - no tiene ningún punto donde ceder, así que en el hilo del loop lo bloquea;
    - el ProcessPoolExecutor la manda a otro proceso pickleándola POR NOMBRE
      (módulo + función), así que tiene que poder importarse desde afuera.
    """
    h = texto.encode()
    for _ in range(iteraciones):
        h = hashlib.sha256(h).digest()
    return h.hex()


async def esperar(segundos: float) -> str:
    await asyncio.sleep(segundos)
    return f'esperé {segundos} s'


async def descargar(urls: list[str]) -> list[dict]:
    """Descarga todas las URLs concurrentemente (gather) y reporta cada una.

    Un cliente por tarea, dentro de un `async with`: si la tarea se cancela
    (DELETE, timeout, apagado), el CancelledError sale del bloque y el cliente
    cierra sus conexiones al salir. Nada queda abierto.
    """
    async with httpx.AsyncClient(timeout=TIMEOUT_POR_URL, follow_redirects=True) as cliente:
        return await asyncio.gather(*(_bajar_una(cliente, url) for url in urls))


async def _bajar_una(cliente: httpx.AsyncClient, url: str) -> dict:
    t0 = time.perf_counter()
    try:
        r = await cliente.get(url)
        # Un 404 o un 500 NO es un error nuestro: es una respuesta válida del remoto
        return {'url': url, 'codigo': r.status_code, 'bytes': len(r.content),
                'segundos': round(time.perf_counter() - t0, 3)}
    except httpx.HTTPError as e:
        # Sin respuesta (DNS, conexión rechazada, timeout de esta URL): se reporta
        # para esta URL y las demás siguen. CancelledError NO es HTTPError: sube.
        return {'url': url, 'error': f'{type(e).__name__}: {e}',
                'segundos': round(time.perf_counter() - t0, 3)}

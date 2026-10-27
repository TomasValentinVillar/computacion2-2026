"""Las funciones que hacen el trabajo de cada tipo: descargar, hashear, esperar."""
import asyncio
import hashlib


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

import time
from functools import wraps

def retry(max_attempts=3, delay=1, exceptions=(Exception,)):
    # Nivel 1: recibe la configuración del decorador
    def decorador(funcion):
        # Nivel 2: recibe la función a decorar
        @wraps(funcion)
        def wrapper(*args, **kwargs):
            # Nivel 3: lógica de reintentos
            ultimo_error = None
            for intento in range(max_attempts):
                try:
                    return funcion(*args, **kwargs)
                except exceptions as e:
                    ultimo_error = e
                    if intento < max_attempts - 1:
                        print(f"Intento {intento+1}/{max_attempts} falló: {e}. Esperando {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"Intento {intento+1}/{max_attempts} falló: {e}.")
            raise ultimo_error   # Relanza el último error
        return wrapper
    return decorador
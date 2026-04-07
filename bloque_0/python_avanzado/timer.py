import time
from contextlib import contextmanager

#Forma 1

class Timer:
    def __init__(self, nombre=None):
        self.nombre = nombre
        self._inicio = None
        self._fin = None

    @property
    def elapsed(self):
        # Si ya terminó el bloque, devuelve el tiempo final
        # Si todavía está corriendo, calcula hasta ahora
        if self._fin is not None:
            return self._fin - self._inicio
        return time.time() - self._inicio

    def __enter__(self):
        self._inicio = time.time()
        return self   # Esto es lo que recibe la variable después del 'as'

    def __exit__(self, tipo_exc, valor_exc, traceback):
        self._fin = time.time()
        if self.nombre is not None:
            print(f"[Timer] {self.nombre}: {self.elapsed:.3f}s")
        return False   # No suprimir excepciones


#Forma 2

class _TimerState:
    # Objeto simple para guardar estado y exponer 'elapsed'
    def __init__(self):
        self._inicio = time.time()
        self._fin = None

    @property
    def elapsed(self):
        if self._fin is not None:
            return self._fin - self._inicio
        return time.time() - self._inicio

@contextmanager
def Timer(nombre=None):
    estado = _TimerState()
    try:
        yield estado   # Acá se ejecuta el bloque with
    finally:
        estado._fin = time.time()
        if nombre is not None:
            print(f"[Timer] {nombre}: {estado.elapsed:.3f}s")
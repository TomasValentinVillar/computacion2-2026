"""Modelos Pydantic: qué acepta el POST y qué devuelven los GET.

Validar acá (en la entrada) y no en el worker: fail fast. Ver notas.md.
"""
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, HttpUrl

# Límites medidos, no supuestos: 1 millón de SHA-256 tarda ~0.96 s en mi máquina.
MAX_ITERACIONES = 20_000_000   # ~20 s de CPU
MAX_URLS = 50                  # la medición 1 pide 20 descargas concurrentes
TIMEOUT_DEFAULT = 30           # cubre un hashear de MAX_ITERACIONES con margen

Estado = Literal['pendiente', 'ejecutando', 'completada', 'fallida', 'cancelada']


# --- Parámetros: uno por tipo, con sus restricciones ---

class ParamsEsperar(BaseModel):
    segundos: float = Field(gt=0)


class ParamsHashear(BaseModel):
    texto: str
    iteraciones: int = Field(gt=0, le=MAX_ITERACIONES)


class ParamsDescargar(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=MAX_URLS)


# --- Lo común a todas las tareas ---

class TareaBase(BaseModel):
    timeout: float = Field(default=TIMEOUT_DEFAULT, gt=0)


# --- Una clase por tipo: fija el 'tipo' y dice qué parámetros lleva ---

class TareaEsperar(TareaBase):
    tipo: Literal['esperar']
    parametros: ParamsEsperar


class TareaHashear(TareaBase):
    tipo: Literal['hashear']
    parametros: ParamsHashear


class TareaDescargar(TareaBase):
    tipo: Literal['descargar']
    parametros: ParamsDescargar


# --- Lo que acepta el POST: "una de estas", elegida según 'tipo' ---

TareaNueva = Annotated[
    Union[TareaEsperar, TareaHashear, TareaDescargar],
    Field(discriminator='tipo'),
]

# Diseño — TP2 Plataforma de Tareas

Referencia del diseño acordado. Se actualiza a medida que se toman decisiones.
Las justificaciones de cada decisión van en `notas.md`.

## Componentes

```
   Cliente HTTP
        |
        v
  ┌──────────────────┐   put    ┌──────────────────┐   get    ┌──────────────────┐
  │   API (FastAPI)  │────────> │  asyncio.Queue   │────────> │  N workers       │
  │  POST/GET/DELETE │          │  (ids)           │          │  (corrutinas)    │
  └────────┬─────────┘          └──────────────────┘          └────────┬─────────┘
           │                                                           │
           │          ┌─────────────────────────────────┐             │
           └─ lee/ ──>│  tareas: dict  id -> datos      │<── escribe ─┘
              escribe │  en_ejecucion: dict id -> Task  │   estado/resultado
                      └─────────────────────────────────┘
```

Todo corre en **un proceso y un hilo** (el event loop de uvicorn). Por eso
los endpoints y los workers comparten los dicts directamente.

## Modelo de una tarea

| Campo | Ejemplo | Quién lo escribe |
|---|---|---|
| `id` | `7` | POST |
| `tipo` | `"descargar"` / `"hashear"` / `"esperar"` | POST |
| `parametros` | `{"segundos": 5}` (solo las claves de su tipo) | POST |
| `timeout` | `10` | POST |
| `estado` | `"pendiente"` | POST, worker, DELETE |
| `resultado` | `None` → `"esperé 5s"` | worker |
| `error` | `None` → `"timeout tras 10s"` | worker |
| `creada` | marca de tiempo | POST |
| `iniciada` | marca de tiempo | worker |
| `finalizada` | marca de tiempo | worker |

Parámetros por tipo:

| Tipo | Parámetros |
|---|---|
| `descargar` | `urls`: lista de URLs |
| `hashear` | `texto`, `iteraciones` |
| `esperar` | `segundos` |

Tiempos derivados:
- **espera en cola** = `iniciada - creada`
- **ejecución** = `finalizada - iniciada`

## Máquina de estados

```
                     ┌──────(1)──────> cancelada
                     │                     ^
                     │                    (3)
                     │                     │
POST ──(0)──> pendiente ──(2)──> ejecutando ┤
                                           ├──(4)──> completada
                                           └──(5)──> fallida
```

| # | Evento | Quién |
|---|---|---|
| 0 | Llega `POST /tareas` válido: se crea en el dict y se encola | endpoint POST |
| 1 | `DELETE` de una tarea que todavía está en la cola | endpoint DELETE |
| 2 | Un worker la saca de la cola y empieza a ejecutarla | worker |
| 3 | `DELETE` de una tarea en ejecución: la API llama a `.cancel()` sobre su `asyncio.Task`; el worker recibe `CancelledError` y la marca | DELETE inicia, worker reacciona |
| 4 | La ejecución termina bien | worker |
| 5 | Vence el timeout, o la ejecución lanza una excepción (ej. URL inexistente) | worker |

Estados finales: `cancelada`, `completada`, `fallida`. Desde un estado final
no se sale: `DELETE` sobre una tarea terminada → **409 Conflict**.

## Respuestas HTTP

| Caso | Código |
|---|---|
| POST aceptado (se procesa después) | 202 |
| Parámetros inválidos (validación Pydantic) | 422 |
| Tarea inexistente | 404 |
| Cancelar una tarea ya terminada | 409 |

## Pendiente de diseñar

- Cómo maneja el worker una tarea que sacó de la cola y ya estaba `cancelada` (flecha 1)
- Qué pasa con los recursos si se cancela a mitad de una descarga
- Executor para `hashear`
- Apagado ordenado (SIGTERM/SIGINT) y volcado a JSON

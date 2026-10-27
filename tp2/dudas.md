# Dudas — TP2

## Para repasar al empezar la próxima sesión

- [ ] `create_task` y guardar los Task para poder cancelarlos
- [ ] Timeout = cancelación con reloj (CancelledError → TimeoutError)
- [ ] `CancelledError` hereda de `BaseException`, no de `Exception` (y por qué)
- [ ] `cancelling()`: distinguir "cancelaron la tarea" (DELETE) de "cancelaron al worker" (apagado)
- [ ] `run_in_executor`: manda la función a otro lado y el `await` libera el loop
- [ ] `ProcessPoolExecutor` picklea la función por nombre (por eso va a nivel de módulo)
- [ ] Thread vs proceso para CPU-bound: el GIL y el costo de pasarlo

## Para el próximo bloque

- `descargar` real (elegir httpx/aiohttp) + medición 1 (20 secuenciales vs 20 concurrentes)
- Apagado ordenado: SIGTERM/SIGINT, esperar máx. 8 s, marcar canceladas las que
  quedaron `ejecutando`/`pendiente`, volcar estado_<timestamp>.json, reportar al arrancar
- Un hash en un proceso del pool NO se corta con cancel()/timeout: ¿qué hacemos?
- `/estadisticas` y medición 3 (techo del pool)

### Repasados

- [x] (26/10) Recorrido del POST, 404 vs return error, validación por anotaciones, deadlock de queue.Queue
- [x] Códigos HTTP: 409 Conflict, y 422 (validación de FastAPI/Pydantic) vs 400
- [x] Validar en la entrada (POST) en vez de dejar que falle en el worker
- [x] `.cancel()` inyecta `CancelledError` en el `await` donde está parada la corrutina
- [x] Discriminador de Pydantic (el error es por el campo que FALTA; lo que sobra se ignora)
- [x] `0.0.0.0` vs `127.0.0.1` dentro de un contenedor
- [x] SIGTERM → PID 1 → 10 s → SIGKILL (explicado; ver notas.md "Apagado ordenado")
- [x] 202 vs 200, dict `tareas` vs cola, trampa del `await`, valores iniciales del POST
- [x] Sólidos sin repaso (sesión 26/10): raise sin argumentos, .cancel() solo pide,
      referencias débiles de create_task, await no crea concurrencia, hash congela
      el loop y el timeout, leer la medición del modo bloqueante
- [x] Sólidos sin repaso: valores iniciales, normalización de HttpUrl, query string,
      sombreado, 404 vs 200 con [], ids en la cola (referencia vs copia), lifespan,
      task_done en finally, except Exception en el worker, concurrencia ≠ paralelismo

## Preguntas abiertas

- ~~Una tarea cancelada mientras está en la cola: ¿qué hace el worker cuando la saca?~~
  → la saltea con `continue` (ver notas.md "Cola y workers")
- Si cancelo una tarea a mitad de una descarga, ¿qué pasa con la conexión abierta?
- ¿Usamos los handlers de señales de uvicorn o ponemos los nuestros para el apagado?
- Cliente HTTP para `descargar`: ¿`httpx` o `aiohttp`? (la consigna pide justificarlo)
- ¿`extra='forbid'` en los modelos para rechazar campos que sobran, o dejarlos pasar?

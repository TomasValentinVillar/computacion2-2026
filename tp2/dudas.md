# Dudas — TP2

## Para repasar al empezar la próxima sesión

- [ ] `put_nowait` vs `await put` con la cola llena: 503 inmediato o el cliente colgado
- [ ] Chequear `cola.full()` ANTES de crear la tarea (y por qué no hace falta Lock hasta el put_nowait)
- [ ] `signal.getsignal()`: guardar el handler que pisamos para devolverle la señal al final

## Para el próximo bloque

- Revisar el borrador del README y escribir la sección 7 ("Lo que aprendí")
- Limpieza final (código, notas.md, README raíz del repo) + prueba completa en Docker
- Bonus si sobra tiempo: tests con pytest-asyncio (cancelación)

### Repasados

- [x] (30/10 tarde) tres estados de una señal, un handler por señal (el último gana),
      backpressure con put_nowait vs await put
- [x] Sólidos sin repaso (sesión 30/10): promedios de /estadisticas, hyperthreading y
      núcleos físicos, crecimiento lineal, cola interna del pool, saturación de la entrada
- [x] (30/10) add_signal_handler vs signal.signal, orden de instalación de handlers
      (el último gana), SIG_DFL/SIG_IGN/manejada, pool sin estado compartido
- [x] Sólidos sin repaso (sesión 29/10 tarde): 503 vs connection refused, los 7 pasos del
      apagado, volumen, fork hereda handlers, hash arrancado no se corta con cancel()
- [x] (29/10 tarde) async with cierra conexiones, except específico (bugs a la vista),
      DNS → TCP → TLS
- [x] Sólidos sin repaso (sesión 29/10): gather vs for con await, 404 como respuesta
      válida, cuello de botella en el remoto, 429 vs 503
- [x] (29/10) create_task guardado, timeout = cancel con reloj, CancelledError fuera de
      Exception, cancelling(), run_in_executor, pickle por nombre, GIL thread vs proceso
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
- ~~Si cancelo una tarea a mitad de una descarga, ¿qué pasa con la conexión abierta?~~
  → el `async with` del cliente la cierra; verificado con `ss` (2 → 0 conexiones)
- ~~¿Usamos los handlers de señales de uvicorn o los nuestros?~~ → los nuestros (503)
- ~~Cliente HTTP para `descargar`: ¿`httpx` o `aiohttp`?~~ → httpx (ver notas.md)
- ¿`extra='forbid'` en los modelos para rechazar campos que sobran, o dejarlos pasar?

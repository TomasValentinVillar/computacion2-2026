# Dudas — TP2

## Para repasar al empezar la próxima sesión

- [ ] 202 Accepted vs 200 OK: por qué el POST devuelve 202
- [ ] El dict `tareas` guarda TODAS las tareas (no hay "lista de pendientes"); la cola es otra cosa
- [ ] La trampa de la versión 1: leer una variable compartida después de un `await`
- [ ] Completar: qué campos escribe el POST y con qué valor inicial (tabla de `diseño.md`)

### Repasados

- [x] Códigos HTTP: 409 Conflict, y 422 (validación de FastAPI/Pydantic) vs 400
- [x] Validar en la entrada (POST) en vez de dejar que falle en el worker
- [x] `.cancel()` inyecta `CancelledError` en el `await` donde está parada la corrutina
- [x] Discriminador de Pydantic (el error es por el campo que FALTA; lo que sobra se ignora)
- [x] `0.0.0.0` vs `127.0.0.1` dentro de un contenedor
- [x] SIGTERM → PID 1 → 10 s → SIGKILL (explicado; ver notas.md "Apagado ordenado")

## Preguntas abiertas

- Una tarea cancelada mientras está en la cola: una `asyncio.Queue` no deja
  sacar un elemento del medio. ¿Qué hace el worker cuando la saca?
- Si cancelo una tarea a mitad de una descarga, ¿qué pasa con la conexión abierta?
- ¿Usamos los handlers de señales de uvicorn o ponemos los nuestros para el apagado?
- Cliente HTTP para `descargar`: ¿`httpx` o `aiohttp`? (la consigna pide justificarlo)
- ¿`extra='forbid'` en los modelos para rechazar campos que sobran, o dejarlos pasar?

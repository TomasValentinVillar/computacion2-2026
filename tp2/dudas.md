# Dudas — TP2

## Para repasar al empezar la próxima sesión

- [ ] Códigos HTTP: 409 Conflict, y 422 (validación de FastAPI/Pydantic) vs 400
- [ ] Validar en la entrada (POST) en vez de dejar que falle en el worker
- [ ] `.cancel()` inyecta `CancelledError` en el `await` donde está parada la corrutina

## Preguntas abiertas

- Una tarea cancelada mientras está en la cola: una `asyncio.Queue` no deja
  sacar un elemento del medio. ¿Qué hace el worker cuando la saca?
- Si cancelo una tarea a mitad de una descarga, ¿qué pasa con la conexión abierta?

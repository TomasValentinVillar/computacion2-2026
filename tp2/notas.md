# Notas de diseño — TP2 Plataforma de Tareas

## Modelo de datos

**Tarea del TP ≠ asyncio.Task**: una tarea es un DATO (registro en un dict) que
existe desde el POST y queda guardado para siempre, para que el GET la pueda consultar.
Un asyncio.Task es la EJECUCIÓN: existe solo mientras un worker la está
corriendo. Una tarea pendiente no tiene corrutina; una completada ya no la necesita.

**Estado compartido en un dict común**: los endpoints y los workers leen/escriben
el mismo dict `tareas` (id -> datos). Funciona sin Manager (a diferencia del TP1)
porque todo corre en UN proceso y UN hilo: mismo espacio de memoria.

**Parámetros en un dict**, no en una lista ni en un campo por cada uno: cada tipo
recibe cosas distintas. Dict = claves con nombre (`{"segundos": 5}`) en vez de
posiciones ambiguas (`["hola", 1000]`), y solo lleva las claves de su tipo.

**Tres marcas de tiempo** (creada / iniciada / finalizada): con dos no se distingue
cuánto esperó en cola de cuánto tardó en ejecutarse. Espera alta = faltan workers;
ejecución alta = la tarea es cara.

## Estados

**cancelada vs fallida**: cancelada = la cortó el cliente (DELETE). fallida = vence el
timeout o una excepción (ej. URL inexistente). Las dos interrumpen, pero la
causa es distinta y se reporta distinto (fallida lleva el motivo en `error`).

**DELETE sobre una tarea terminada → 409 Conflict**: el pedido es válido pero choca
con el estado actual del recurso. (404 = no existe, 400/422 = pedido mal formado.)

**Validar en la entrada**: parámetros inválidos se rechazan en el POST con Pydantic
(422), no se dejan fallar en el worker. Ej: `hashear` con iteraciones=-3 NO tira
error (`range(-3)` no itera) y devolvería un hash sin sentido.

## Concurrencia

**Un hilo, sin Lock**: el event loop alterna corrutinas y el cambio solo ocurre en un
`await` que suspende. Entre dos `await` el código corre de corrido y nadie lo interrumpe.
Por eso no hace falta Lock, SALVO que haya un `await` en medio de la sección crítica.

**Cancelar una tarea en ejecución**: la API necesita el asyncio.Task de ESA tarea
para llamar `.cancel()`. Se guarda en un segundo dict `en_ejecucion` (id -> Task)
que solo tiene entradas mientras se ejecuta. `.cancel()` inyecta CancelledError
en el `await` donde la corrutina está parada (no en cualquier línea).

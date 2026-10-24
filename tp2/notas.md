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
Verificado: `asyncio.run(asyncio.sleep(-5))` termina al instante SIN error.
O sea, un `esperar` con -5 que llegue al worker terminaría `completada`: el cliente
recibe 202, después "completada", y nunca se entera de que mandó algo sin sentido.
Peor que fallar: un éxito falso. Validar en el POST (fail fast) da 422 al instante
y no gasta lugar en la cola ni worker.

**DELETE exitoso → 200** si devuelve la tarea actualizada en el cuerpo; 204 No Content
si no devuelve nada.

## Validación con Pydantic (modelos.py)

**Un modelo por tipo de tarea + discriminador** (opción elegida entre 3):
- A) un modelo por tipo, Pydantic elige según `tipo` ← ELEGIDA
- B) un modelo con validador propio lleno de `if tipo == ...`
- C) validar a mano en el endpoint
Motivos: reglas declarativas (no `if`s), mensajes de error automáticos, cada tipo
aparece con sus campos en /docs, y agregar una tarea nueva = agregar una clase
SIN tocar las existentes (principio abierto/cerrado).
Con `parametros: dict` Pydantic no puede validar el contenido: para él es
"cualquier dict", así que `{"segundos": -5}` o `{"banana": 3}` pasarían.

**discriminator='tipo'**: Pydantic mira `tipo` primero y valida SOLO con esa clase.
Sin discriminador probaría las tres y mostraría los errores de las tres mezclados.

**Literal en vez de str** para `tipo`: un tipo inexistente ("bailar") lo rechaza
Pydantic solo, con un 422 que lista los válidos.

**Límites medidos, no supuestos**: 1 millón de SHA-256 = 0.96 s en mi máquina
(medido con perf_counter) → 1 iteración ≈ 1 µs.
- `iteraciones` ≤ 20 millones (~20 s): alcanza para bloquear el loop de forma visible
  (medición 2), sin dejar que alguien cuelgue el servidor por minutos.
  OJO: una IA (Gemini) hizo la cuenta tomando 1 iteración = 1 ms y daba días;
  con mi medición la cuenta correcta es 100 millones ≈ 1.6 min.
- `urls`: entre 1 y 50 (la medición 1 pide 20 concurrentes, +margen).
  `list[HttpUrl]` valida que cada elemento sea una URL con http/https.
- `timeout`: default 30 s (cubre un hashear máximo con margen), `gt=0`.

**Inválido vs imprudente**: el servidor rechaza lo que nunca tiene sentido
(timeout ≤ 0). Un timeout de 0.5 s es válido aunque sea poco prudente: lo decide
el cliente, y además sirve para probar timeouts rápido.

Verificado con TypeAdapter: esperar -5 → 422, tipo "bailar" → 422, 1000 millones
de iteraciones → 422, lista vacía → 422, "hola" como URL → 422.

**Campos que sobran se ignoran**: verificado con TypeAdapter, `{"segundos": 2,
"texto": "hola"}` en un `esperar` PASA (Pydantic descarta `texto` en silencio).
Sin `segundos` → 422 "Field required" (el error es por lo que FALTA, no por lo que
sobra). Para rechazar lo que sobra existe `extra='forbid'`. → PENDIENTE decidir.

## Ids y estado compartido (estado.py)

**Contador entero, no UUID**: más cómodo para probar a mano (`curl .../tareas/7`).
El riesgo del contador (ids repetidos) no existe acá: `nuevo_id()` no tiene ningún
`await`, y con un solo hilo el event loop no puede meter otro POST entre el
incremento y el return → atómico sin Lock.

**Después de un await, el estado compartido puede haber cambiado**. Dos versiones
con `await` adentro fallan, y no solo la obvia:
- leer → await → escribir: dos llamadas leen el mismo valor → id repetido.
- incrementar → await → `return _ultimo_id`: el incremento está bien, pero el return
  lee la global DESPUÉS del await y devuelve el valor que dejó OTRA llamada.
Arreglo: copiar a una variable local antes del await (`mi_id = _ultimo_id`).
Esto va a aparecer en los workers: leer `tarea['estado']`, await, y el DELETE
pudo haberla cancelado en el medio.

**`tareas` guarda TODAS las tareas**, en cualquier estado. No hay "lista de
pendientes": `pendiente` es el valor del campo `estado`. La cola es otra cosa.

## Apagado ordenado (diseño)

Docker manda SIGTERM, espera 10 s y manda SIGKILL. SIGKILL mata el proceso entero:
hilos y corrutinas incluidos. Y si muere el PID 1, el kernel mata TODO el namespace
de PIDs (el contenedor entero). Por eso escribir el JSON en otro proceso, hilo o
corrutina NO lo salva.
Lo lento es esperar a las tareas, no escribir el JSON (milisegundos). El problema
es CUÁNDO se escribe, no CÓMO. Orden:
1. dejar de aceptar tareas nuevas
2. esperar las tareas en curso, MÁXIMO 8 s (margen antes del SIGKILL)
3. cancelar las que no terminaron
4. escribir estado_<timestamp>.json
5. salir
`stop_grace_period` en el compose estira los 10 s, pero solo con TU compose
(`docker stop` a mano vuelve a 10 s): el código no debe depender de eso.
**Pendientes al apagar → `cancelada`** en el JSON: nadie las va a ejecutar, así que
`pendiente` sería mentir. (Si hubiera un bonus de "reanudar al reiniciar", ahí sí
tendría sentido dejarlas pendientes.)

## Docker

**host 0.0.0.0 y no 127.0.0.1**: 127.0.0.1 es el loopback DEL CONTENEDOR; el curl
desde el host entra por el mapeo de puertos a la interfaz de red del contenedor
(172.x), así que solo se atiende si el servidor escucha en todas las interfaces.

**CMD en forma exec** (`["python", "main.py"]`): python queda como PID 1 y recibe
directo el SIGTERM de `docker compose stop`. Docker espera 10 s y después manda
SIGKILL (no capturable) → el apagado ordenado tiene que entrar en ese margen.
PID 1 es especial: el kernel IGNORA las señales sin handler instalado, así que
si nadie captura SIGTERM, el proceso no se entera y muere por SIGKILL a los 10 s.

**Docker desde el principio, híbrido**: venv + `uvicorn --reload` para iterar,
`docker compose up --build` al cerrar cada sesión (lección del TP1: los
problemas de Docker conviene encontrarlos temprano).

## Estructura

Archivos planos en `src/`, sin subcarpetas (cada tarea son ~20 líneas):
main.py (API), modelos.py (Pydantic), estado.py (dicts), workers.py (cola + pool),
tareas.py (descargar/hashear/esperar). "¿Dónde puede bloquear el loop?" → tareas.py
y workers.py.

## Concurrencia

**Un hilo, sin Lock**: el event loop alterna corrutinas y el cambio solo ocurre en un
`await` que suspende. Entre dos `await` el código corre de corrido y nadie lo interrumpe.
Por eso no hace falta Lock, SALVO que haya un `await` en medio de la sección crítica.

**Cancelar una tarea en ejecución**: la API necesita el asyncio.Task de ESA tarea
para llamar `.cancel()`. Se guarda en un segundo dict `en_ejecucion` (id -> Task)
que solo tiene entradas mientras se ejecuta. `.cancel()` inyecta CancelledError
en el `await` donde la corrutina está parada (no en cualquier línea).
Verificado con un script: tarea() hace print("A"), await sleep(3), print("B");
main() la cancela al segundo. Salida: "A", y después CancelledError en main.
"B" NUNCA se imprime: la excepción aparece en el `await sleep(3)` y corta ahí.
`main` PIDE la cancelación (t.cancel()); `tarea` la RECIBE en su await. Son dos
lugares distintos → el try/except CancelledError del worker va alrededor del await.
Si tarea() estuviera en una línea sin await (un cálculo), el cancel ni siquiera
puede llegar: con un solo hilo, main() no corre mientras tarea() calcula.

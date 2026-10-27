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

## Endpoints (main.py)

**POST → 202 con la tarea recién creada** (id + `pendiente`), sin resultado: el
cliente lo consulta después con GET /tareas/{id}. Valores iniciales: `None` para
lo que todavía no pasó (resultado, error, iniciada, finalizada); `creada =
time.time()` (número simple, se vuelca directo al JSON).
`parametros` se guarda con `model_dump(mode='json')`: las HttpUrl pasan a str,
así el dict es serializable para el volcado.

**La validación sale de las anotaciones de tipo, no de una línea de código**:
FastAPI lee la firma del endpoint (`nueva: TareaNueva`, `estado_filtro: Estado`) y
valida ANTES de llamar a la función. Si falla, responde 422 y la función ni se
ejecuta. Pydantic además NORMALIZA: "https://example.com" se guarda como
"https://example.com/".

**HTTPException(404) y no `return {"error": ...}`**: el return respondería 200, y un
programa (script, test, medición) mira el código antes que el cuerpo → creería
que salió bien. El código HTTP tiene que decir la verdad por sí solo.

**GET /tareas?estado=X**: el filtro va en el query string. `Estado` es un Literal de
los 5 estados → "bailando" da 422 solo. Colección vacía → 200 con `[]`, no 404: la
colección existe aunque no tenga elementos; 404 es para UN recurso que no existe.
El parámetro se llama `estado_filtro` con `alias='estado'`: si se llamara `estado`
taparía al módulo `estado` adentro de la función (sombreado).

## Cola y workers (workers.py)

**asyncio.Queue y no queue.Queue**: `queue.Queue.get()` con la cola vacía bloquea
el HILO, o sea el event loop entero. El worker espera un item que solo un POST
puede poner, pero el POST no puede ejecutarse → deadlock, todo congelado.
`await cola.get()` suspende solo esa corrutina y el loop sigue atendiendo.

**En la cola van ids, no dicts**: una sola fuente de verdad (`estado.tareas`) y el
worker ve el estado ACTUAL al sacarla. (Ojo: meter el dict también "andaría",
porque la cola guarda una REFERENCIA al mismo objeto, no una copia. Con
multiprocessing.Queue sí sería una copia: se picklea a otra memoria.)

**Workers en el lifespan**: `create_task` necesita un loop corriendo, y al importar
el módulo no lo hay. `lifespan` es un context manager async: antes del yield =
arranque (loop ya corriendo, antes del primer pedido), después = apagado.
Se guardan los Task en `_workers` para poder cancelarlos al apagar.

**N_WORKERS por variable de entorno** (default 4): configurable sin tocar código
(sirve para la medición 3). `int()` porque las variables de entorno son strings.

**Dentro del worker**:
- tarea `cancelada` mientras estaba en cola → `continue` (no se puede sacar un
  elemento del medio de una asyncio.Queue; se saltea al sacarla).
- `task_done()` en un `finally`: se llama pase lo que pase. Verificado: el finally
  corre también con `continue`. Si faltara un task_done, `cola.join()` del apagado
  esperaría para siempre.
- `except Exception`: una tarea que falla no mata al worker. Sin eso, la excepción
  rompe el `while True` y se pierde un worker en silencio.
- `ejecutar()` hace el trabajo y devuelve el resultado; el worker administra el
  estado. Separación de responsabilidades.

**Timeout = cancelación con reloj**: `async with asyncio.timeout(N)` cancela lo de
adentro al vencer (CancelledError en el await donde está parada) y al salir lo
convierte en TimeoutError.

**Verificado** con 4 workers, 6 `esperar` de 2 s y uno de 3 s con timeout 1:
- t=0.3 s: exactamente 4 ejecutando (uno por worker), 3 pendientes.
- Las 4 primeras terminaron a los ~2 s, NO a los 8 s.
- Las 5-7 estuvieron ~1.9 s en cola (esperando que se libere un worker).
- La 7 duró exactamente 1.00 s y quedó `fallida: timeout: superó 1.0 s`.
Sin las tres marcas de tiempo no se vería la espera en cola.

**Concurrencia ≠ paralelismo**: con un hilo nunca se ejecutan dos líneas a la vez.
Los 4 workers llegan a su `await sleep(2)` uno tras otro en microsegundos y
después los 4 ESPERAN a la vez. Se superponen las esperas, no la ejecución → sirve
para I/O (esperar, descargar), no para CPU (hashear).

## DELETE y cancelación de una tarea en ejecución

**No se cancela al worker**: `CancelledError` hereda de BaseException, NO de
Exception, a propósito (si un `except Exception` genérico se tragara las
cancelaciones, nada se podría cancelar). Nuestro `except Exception` no lo atrapa:
sube, corre el finally, rompe el `while True` → se pierde el worker.

**Cada ejecución corre en su propio Task** (`create_task(ejecutar(tarea))`), guardado
en `estado.en_ejecucion[tid]`. El DELETE cancela ESE Task; el worker sigue vivo.
El `await t` del worker también recibe CancelledError → hay que distinguir:
`asyncio.current_task().cancelling()` = pedidos de cancelación contra el WORKER.
- 0 → cancelaron solo la tarea (DELETE) → marcar `cancelada` y seguir.
- >0 → cancelaron al worker (apagado) → `raise` y morir.
`raise` sin argumentos relanza la misma excepción: lo que sigue NO se ejecuta.

**DELETE pone `cancelada` él mismo**: `.cancel()` solo PIDE; el CancelledError le
llega a la tarea recién cuando el loop la retoma, o sea DESPUÉS de que el DELETE
responde (no tiene await entre cancel() y return). `cancel()` devuelve False si el
Task ya terminó → 409.

**Verificado** (1 worker): DELETE de pendiente → 200, el worker la saltea
(`iniciada` queda None); DELETE en ejecución → 200 y el worker toma la siguiente;
DELETE de completada → 409; inexistente → 404; el worker sigue vivo después.
Apagado con una tarea corriendo → cierre limpio (gather con return_exceptions).

**PENDIENTE para el apagado**: con el `raise`, una tarea que estaba ejecutando al
apagar queda en `ejecutando` (nadie la marca) → el JSON mentiría.

## hashear y el executor (medición 2)

**`await` no crea concurrencia**: solo marca dónde la corrutina PODRÍA ceder. Una
función `async def` que adentro solo calcula se ejecuta de corrido igual. Con el
hash en el hilo del loop, se congela TODO (GETs, otros workers y hasta el reloj de
asyncio.timeout, que también lo maneja el loop). Mismo bug que time.sleep().

**`run_in_executor(pool, funcion, args)`**: manda la función a otro hilo/proceso y
devuelve un future; el `await` suspende solo a esa corrutina y el loop sigue.
`hashear` es una función común a nivel de módulo: el ProcessPoolExecutor la
picklea POR NOMBRE para mandarla al otro proceso.

**MODO_CPU configurable** (proceso / thread / bloqueante) para poder medir las tres.

**Medición** (`mediciones/medir_cpu.py`): 4 hashes de 5M iteraciones a la vez,
GET /tareas cada 0.1 s mientras tanto. 8 núcleos.

| MODO_CPU   | total  | GETs en el lapso | latencia GET prom. | peor   |
|------------|--------|------------------|--------------------|--------|
| bloqueante | 14.2 s | 1                | 3535 ms            | 3535 ms|
| thread     | 33.5 s | 73               | 357 ms             | 1279 ms|
| proceso    | 4.1 s  | 40               | 2.0 ms             | 3.6 ms |

Hipótesis vs resultado:
- thread, ¿responde el GET? Dije sí → a medias (357 ms prom., hasta 1.3 s).
- thread, total: dije ~4× (secuencial) → PEOR: 33.5 s, más del doble que bloqueante.
- proceso: dije que responde y ~1× → acerté las dos.

Interpretación:
- **bloqueante**: el servidor estuvo sordo 14 s. El único GET entró en el hueco
  entre un hash y el siguiente → tardó lo que un hash (14.2/4 ≈ 3.5 s).
- **thread**: el GIL deja correr un hilo a la vez Y además cada traspaso cuesta.
  5 hilos (4 del pool + el del loop) se pelean el GIL; Python obliga a soltarlo
  cada 5 ms (sys.getswitchinterval()), cada traspaso = despertar otro hilo
  (context switch) en otro núcleo con la caché fría. Miles de traspasos = los
  19 s extra. Para CPU-bound, threads son PEORES que nada: solo evitan congelar
  del todo el loop.
- **proceso**: un GIL por proceso → paralelismo real. 4 hashes tardan lo que 1.

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

# TP2 — Plataforma de Tareas Distribuidas

**Tomás Villar** · Computación II · Universidad de Mendoza · 2026

Un servicio HTTP al que se le encargan trabajos, que los ejecuta de forma
concurrente y permite consultar su estado, cancelarlos y apagarse sin perder nada.
Hecho con FastAPI, `asyncio` y un `ProcessPoolExecutor` para lo que es CPU-bound.

> La bitácora completa del desarrollo, con cada decisión, cada verificación y los
> errores que encontré midiendo, está en [`notas.md`](notas.md). Este README es el
> resumen ordenado; cuando una sección dice "ver notas", el detalle está ahí.

---

## 1. Descripción y uso

### Levantarlo

```bash
docker compose up --build
```

La API queda en `http://localhost:8000` y la documentación interactiva en
`http://localhost:8000/docs`, donde cada tipo de tarea aparece con sus campos.

### Tipos de tarea

| Tipo | Naturaleza | Parámetros | Qué devuelve |
|---|---|---|---|
| `descargar` | I/O-bound | `urls`: entre 1 y 50 URLs | por cada URL: código, bytes y segundos (o el error de esa URL) |
| `hashear` | CPU-bound | `texto`, `iteraciones` (1 a 20 millones) | SHA-256 aplicado N veces |
| `esperar` | I/O simulado | `segundos` (> 0) | `"esperé N s"` |

Todas aceptan además `timeout` (segundos, por defecto 30).

### Endpoints

| Método | Ruta | Respuestas |
|---|---|---|
| `POST` | `/tareas` | **202** encolada · **422** parámetros inválidos · **503** cola llena o apagándose |
| `GET` | `/tareas?estado=X` | **200** lista (vacía si no hay) · **422** estado inexistente |
| `GET` | `/tareas/{id}` | **200** · **404** |
| `DELETE` | `/tareas/{id}` | **200** cancelada · **404** · **409** ya terminó |
| `GET` | `/estadisticas` | **200** totales por estado, workers ocupados, tiempos promedio |

Estados: `pendiente` → `ejecutando` → `completada` / `fallida` / `cancelada`.

### Ejemplos con `curl`

```bash
# Encolar: responde enseguida con el id, sin esperar a que la tarea termine
curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "esperar", "parametros": {"segundos": 5}}'

curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "descargar", "parametros": {"urls": ["https://example.com", "https://httpbin.org/status/404"]}}'

curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "hashear", "parametros": {"texto": "hola", "iteraciones": 5000000}, "timeout": 60}'

# Consultar
curl localhost:8000/tareas/1
curl "localhost:8000/tareas?estado=ejecutando"
curl localhost:8000/estadisticas

# Cancelar (pendiente o en ejecución)
curl -X DELETE localhost:8000/tareas/1

# Probar el timeout: duerme 5 s con un límite de 1 s → 'fallida'
curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "esperar", "parametros": {"segundos": 5}, "timeout": 1}'
```

### Apagado ordenado

`docker compose stop` (SIGTERM) o Ctrl+C (SIGINT) dejan de aceptar tareas,
esperan hasta 8 s a las que están en curso, cancelan las que quedan y vuelcan todo
a `datos/estado_<timestamp>.json`. Al volver a levantarlo, el log reporta el último
volcado:

```
INFO:     volcado previo: estado_20261030_001417.json (3 tareas: {'completada': 1, 'cancelada': 2})
```

### Configuración (variables de entorno)

| Variable | Default | Para qué |
|---|---|---|
| `N_WORKERS` | 4 | cantidad de workers (corrutinas) del pool |
| `MAX_COLA` | 1000 | tareas esperando como máximo; más allá, el POST responde 503 |
| `MODO_CPU` | `proceso` | dónde corre `hashear`: `proceso`, `thread` o `bloqueante` (los dos últimos existen para la medición 2) |
| `DIR_ESTADO` | `datos/` | dónde se escriben los volcados (en Docker, un volumen) |

### Fuera de Docker

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
cd src && ../venv/bin/python main.py
```

---

## 2. Arquitectura

```
                         un proceso, un hilo: el event loop
 ┌────────────────────────────────────────────────────────────────────────────┐
 │                                                                            │
 │   Cliente ──HTTP──> API (FastAPI)                                          │
 │                      │  POST: valida (Pydantic) → id → guarda → encola id  │
 │                      │  GET / DELETE / estadisticas: leen el dict          │
 │                      ▼                                                     │
 │      ┌──────────────────────────┐   put_nowait(id)   ┌──────────────────┐  │
 │      │ estado.tareas            │ ─────────────────> │ asyncio.Queue    │  │
 │      │   id -> datos (siempre)  │                    │ (maxsize, ids)   │  │
 │      │ estado.en_ejecucion      │                    └────────┬─────────┘  │
 │      │   id -> Task (mientras   │                             │ await get  │
 │      │   corre: para cancelar)  │ <── lee / escribe ──┐       ▼            │
 │      └──────────────────────────┘                     │  N workers         │
 │                                                       └─ (corrutinas)      │
 │                                                           │     │          │
 │                       esperar / descargar: await directo ─┘     │          │
 │                       en el loop (I/O, ceden mientras esperan)  │          │
 │                                                                 │          │
 └─────────────────────────────────────────────────────────────────┼──────────┘
                                                run_in_executor    │ pickle
                                                                   ▼
                                     ┌───────────────────────────────────────┐
                                     │ ProcessPoolExecutor (1 proceso/núcleo)│
                                     │ hashear: CPU-bound, un GIL por proceso│
                                     │ "calculadoras": no tocan el estado    │
                                     └───────────────────────────────────────┘
```

### El flujo de una tarea

```
POST ─> Pydantic valida ─> id ─> dict: 'pendiente' ─> cola ─> 202 (inmediato)
                                                        │
          worker: await cola.get() <────────────────────┘
            ├─ ¿ya 'cancelada'? (DELETE mientras esperaba) → la saltea
            ├─ 'ejecutando' + iniciada
            ├─ Task propio para ejecutarla (guardado en en_ejecucion)
            │   dentro de asyncio.timeout(tarea.timeout)
            ├─ termina bien             → 'completada' + resultado
            ├─ vence el timeout         → 'fallida' + "timeout: superó N s"
            ├─ excepción                → 'fallida' + motivo
            ├─ DELETE (.cancel())       → 'cancelada'
            └─ siempre: finalizada, sale de en_ejecucion, task_done()

GET /tareas/{id} ─> lee el dict, cuando el cliente quiera
```

Archivos (`src/`): `main.py` (API, señales, apagado) · `modelos.py` (validación) ·
`estado.py` (los dicts) · `workers.py` (cola, workers, executor) · `tareas.py` (el
trabajo) · `persistencia.py` (volcado y reporte). Las preguntas "¿dónde puede
bloquear el loop?" se responden mirando dos archivos: `tareas.py` y `workers.py`.

---

## 3. Decisiones de diseño

### ¿Por qué `asyncio.Queue` y no `queue.Queue`?

Porque todo corre en **un solo hilo**. `queue.Queue.get()` con la cola vacía
bloquea **el hilo**, o sea el event loop entero: el worker se queda esperando un
item que solo un POST puede poner, pero el POST no puede ejecutarse porque el loop
está bloqueado. Es un **deadlock**. `await cola.get()` suspende **solo a esa
corrutina** y el loop sigue atendiendo pedidos.

Por la misma razón el pool **no necesita `Lock`**: el loop solo cambia de corrutina
en un `await`, y entre dos `await` el código corre de corrido. Ejemplo:
`nuevo_id()` incrementa un contador sin Lock y nunca da ids repetidos, porque no
tiene ningún `await` adentro. (El Lock haría falta si hubiera un `await` en medio
de una sección crítica; ver notas, "Ids y estado compartido".)

En la cola van **ids, no dicts**: la única fuente de verdad es `estado.tareas`, y el
worker ve el estado **actual** cuando la saca (por ejemplo, si un DELETE la canceló
mientras esperaba).

### ¿Cómo evito que una tarea CPU-bound congele la API?

`hashear` se manda a un **`ProcessPoolExecutor`** con `loop.run_in_executor()`.
El `await` suspende solo a ese worker mientras otro proceso calcula, y el loop sigue
libre. Elegí **procesos y no threads** porque lo medí (medición 2): con threads, el
GIL deja correr un hilo a la vez y encima cobra por cada traspaso; 4 hashes
tardaron **más del doble** que haciéndolos uno tras otro en el loop.

Poner `async def` o `await` delante de un cálculo **no sirve**: `await` solo marca
dónde una corrutina *podría* ceder; si adentro no hay nada que suspenda, se
ejecuta de corrido. Es el mismo bug que `time.sleep()` en una corrutina.

Los procesos del pool son "calculadoras": reciben `(texto, iteraciones)` por pickle
y devuelven un string. No tocan el dict ni la cola, así que no hace falta `Manager`.

### ¿Cómo implementé la cancelación, y qué pasa con los recursos a medio usar?

- **Pendiente**: no se puede sacar un elemento del medio de una `asyncio.Queue`.
  El DELETE la marca `cancelada` y el worker la saltea cuando la saca.
- **En ejecución**: cada ejecución corre en **su propio Task**, guardado en
  `en_ejecucion`. El DELETE le hace `.cancel()` a **ese Task, no al worker**, y el
  worker sigue vivo. Como el `await` del worker también recibe el
  `CancelledError`, distingue con `asyncio.current_task().cancelling()`: si es 0,
  cancelaron la tarea (DELETE) y la marca `cancelada`; si no, cancelaron al worker
  (apagado) y lo deja morir.
- `.cancel()` solo *pide*: el `CancelledError` aparece en el `await` donde la
  corrutina está parada, después de que el DELETE ya respondió.

**Recursos**: la descarga usa un cliente httpx dentro de un `async with`. Al
cancelar, el `CancelledError` sale del bloque y el cliente **cierra sus
conexiones**. Lo verifiqué con `ss -tnp`: 2 conexiones establecidas a mitad de una
descarga → DELETE → 0. Solo se atrapa `httpx.HTTPError`, así la cancelación no se
confunde con un error de red. Un **timeout** es lo mismo que un `.cancel()`, pero
disparado por un reloj (`asyncio.timeout`).

La excepción es el hash: un cálculo ya arrancado en otro proceso **no se corta** con
`.cancel()` (ver Limitaciones).

### ¿Qué pasa si un worker lanza una excepción no capturada?

No puede pasar con una tarea: el worker envuelve la ejecución en
`except Exception`, la marca `fallida` con el motivo y sigue con la próxima. Sin
eso, la excepción rompería su `while True` y el pool **perdería un worker en
silencio**. `task_done()` va en un `finally`, así se llama pase lo que pase.

`CancelledError` hereda de `BaseException` y no de `Exception` **a propósito**: si
un `except Exception` genérico se la tragara, nada se podría cancelar. Por eso ese
`except` no interfiere con el DELETE ni con el apagado.

### Otras decisiones

- **Validar en la entrada** (Pydantic, un modelo por tipo con
  `discriminator='tipo'`): lo inválido se rechaza con 422 antes de encolarse. Lo
  descubrí probando: `asyncio.sleep(-5)` **no falla**, así que un `esperar` con
  -5 terminaría `completada`, un éxito falso.
- **Límites medidos, no supuestos**: 1 millón de SHA-256 tarda 0.96 s en mi máquina,
  así que el máximo de 20 millones son ~20 s.
- **`descargar` no falla por una URL**: un 404 es una respuesta válida del remoto y
  se reporta como dato; solo es error cuando no hay respuesta. La tarea es
  `fallida` si fallan todas o si vence su timeout. Elegí httpx (el de la clase 20)
  por su API simple; la ventaja de aiohttp aparece con miles de conexiones.
- **Backpressure**: la cola tiene `maxsize` y el POST responde 503 si está llena,
  con `put_nowait` y no `await put`: este último dejaría al cliente colgado
  esperando lugar.
- **Apagado con handlers propios** (`loop.add_signal_handler`), así un POST durante
  el apagado recibe **503 + Retry-After** en lugar de "connection refused". El
  límite de espera es **8 s** porque Docker manda SIGKILL a los 10. Las tareas sin
  terminar se cancelan **antes** de volcar, para que el JSON no diga `ejecutando` ni
  `pendiente` de algo que nadie va a ejecutar. El volcado va a un **volumen**
  (`./datos`), así sobrevive a `docker compose down`. Al terminar, le pasamos la
  señal al handler de uvicorn que habíamos pisado (guardado con
  `signal.getsignal`) para que el servidor salga: anda igual con `python main.py`
  que con `uvicorn main:app --reload`.

---

## 4. Mediciones

Máquina: Intel i5-8250U, **4 núcleos físicos × 2 hilos** (8 CPUs lógicas). Scripts
en [`mediciones/`](mediciones/). En las mediciones 2 y 3 escribí antes mi hipótesis;
en notas.md están junto al resultado, con lo que acerté y lo que no.

### Medición 1: concurrencia I/O — 20 descargas secuenciales vs concurrentes

`mediciones/medir_io.py`, contra `httpbin.org/delay/1` (una URL que tarda ~1 s por
diseño, para no depender de la velocidad de cada sitio).

| Caso | Total |
|---|---|
| Secuencial (1 worker, 20 tareas de 1 URL) | **40.4 s** |
| Concurrente (1 tarea, 20 URLs con `gather`) | **3.5 s** |
| Concurrente por pool (20 workers, 20 tareas) | 2.2 s (con algún 429) |

**Speedup: ~11.6×.**

- `gather` lanza todas y las 20 **esperas se superponen**: el total es
  aproximadamente la más lenta, no la suma. Un `for` con `await` adentro esperaría
  que termine cada una antes de empezar la siguiente.
- **No llega a 20×** porque el cuello de botella es **el remoto**: una URL que tarda
  1 s por diseño tardó entre 1.9 y 3.3 s con 20 a la vez (httpbin es un servicio
  público y compartido). Mi CPU solo esperaba. En I/O-bound, el techo lo pone el
  otro extremo.
- En el secuencial, cada descarga tardó **como mínimo 1.64 s**: cada tarea abre una
  conexión nueva y paga DNS + handshake TCP + handshake TLS antes del primer byte.
- Con 20 workers, httpbin respondió **429 Too Many Requests**: un rate limit dirigido
  a mi IP. Más concurrencia contra un mismo servidor no siempre es mejor. El
  sistema lo reportó como dato de esa URL, sin romper la tarea.

### Medición 2: el event loop bloqueado

`mediciones/medir_cpu.py`: 4 hashes de 5 millones a la vez, con `GET /tareas` cada
0.1 s mientras corren.

| `MODO_CPU` | Total | GETs atendidos | Latencia GET prom. | Peor |
|---|---|---|---|---|
| `bloqueante` (sin executor) | 14.2 s | **1** | **3535 ms** | 3535 ms |
| `thread` | **33.5 s** | 73 | 357 ms | 1279 ms |
| `proceso` | **4.1 s** | 40 | **2.0 ms** | 3.6 ms |

- **Sin executor**, el servidor estuvo **sordo 14 segundos**: el único GET entró en
  el hueco entre un hash y el siguiente, y tardó lo que tarda un hash (14.2 / 4).
- **Con threads** responde, pero lento, y el total fue **peor que sin executor**.
  Cinco hilos (4 del pool y el del loop) se pelean el GIL; Python obliga a soltarlo
  cada 5 ms y cada traspaso es un context switch con la caché fría. Para CPU-bound,
  los threads no paralelizan y además cobran el traspaso.
- **Con procesos**, la API responde en 2 ms como si nada, y 4 hashes tardan lo que
  tarda 1: cada proceso tiene su propio GIL, así que hay paralelismo real.

### Medición 3: el techo del pool

`mediciones/medir_techo.py`: N tareas iguales a la vez, con N workers.

**CPU-bound** (hashear 2M; uno solo tarda ~2.4 s):

| N | 1 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|
| Total | 2.4 s | 2.7 s | 4.1 s | 8.0 s | 14.0 s |

- Plano hasta 4, y empieza a subir en 8: **el techo son los 4 núcleos físicos**.
  Los dos hilos de un núcleo comparten sus unidades de cálculo; para un hash, el
  hyperthreading aportó ~17%. Desde ahí, el crecimiento es **lineal**.
- La API nunca se degradó (GET en milisegundos).
- **Punto ciego**: con 32 workers ninguna tarea esperó en *nuestra* cola, pero la
  "ejecución" promedio dio 8.7 s para un hash de 2.4 s. Esperaron en la **cola
  interna del `ProcessPoolExecutor`**, que nuestra métrica no ve.

**I/O-bound** (esperar 1 s):

| N | 10 | 100 | 1.000 | 10.000 |
|---|---|---|---|---|
| Ejecución promedio | 1.00 s | 1.01 s | 1.00 s | 1.01 s |
| Envío de los POST | 0.05 s | 0.28 s | 0.95 s | **8.3 s** |
| Memoria del servidor | 47 MB | 48 MB | 51 MB | 76 MB |

- El event loop **no se rompió** con 10.000 corrutinas durmiendo: cada una siguió
  tardando 1.01 s.
- Lo primero que se satura es **la entrada de la API**: recibir 10.000 POST (parsear
  HTTP, validar, responder) en un solo hilo llevó 8.3 s (~1.200 pedidos/s).
- Cada tarea ocupa ~1.7 KB. Con 10.000 es poco; con un millón serían ~1.7 GB. Por
  eso agregué el límite de la cola (503 al llenarse).

**"Si te mando 10.000 tareas de golpe, ¿qué se rompe primero?"**: no se rompe el
event loop. Primero tarda la entrada de pedidos; con pocos workers, se llena la
cola y el POST empieza a responder 503 en lugar de acumular sin límite.

---

## 5. Conceptos del curso aplicados

| En el código | Concepto | Clase |
|---|---|---|
| Workers que consumen ids de una `asyncio.Queue` | Productor-consumidor, el mismo patrón que con threads pero con corrutinas: sin Lock, porque el loop no interrumpe entre `await`s | 11, 21 |
| Todo el servidor en un hilo con un event loop | El loop es un `select`/`epoll` que despierta a la corrutina cuyo socket está listo | 17 |
| `await` en workers y descargas | Corrutinas como generadores que se suspenden y se retoman; scheduler cooperativo | 18 |
| `POST` 202, `DELETE` 409, 422, 503, query string | Métodos y códigos de estado HTTP; FastAPI valida desde las anotaciones de tipo | 19 |
| `gather` en `descargar`, `asyncio.timeout`, `.cancel()` | Clientes concurrentes, timeouts y cancelación | 20 |
| `run_in_executor` con `ProcessPoolExecutor`, `lifespan` | Sacar el trabajo pesado del loop; tareas que nacen y mueren con la app | 21 |
| `async with httpx.AsyncClient`, `lifespan` | Context managers: liberar recursos pase lo que pase | Bloque 0 |
| DNS + handshake TCP + TLS en cada conexión nueva | Lo que cuesta abrir una conexión (medición 1) | 12, 13 |
| Más workers que núcleos → tiempos lineales | Pool de tamaño fijo y su techo | 14 |
| `add_signal_handler`, SIG_DFL / SIG_IGN en el pool | Señales: por defecto, ignorada o manejada; el hijo de un `fork` hereda los handlers | Señales y procesos (TP1) |
| Procesos y no threads para el hash | GIL: un intérprete por proceso para tener paralelismo real | Multiprocessing (TP1) |

Un ejemplo concreto del último par: el pool de procesos hace `fork` **después** de
que instalamos nuestro handler de SIGTERM. Los hijos lo heredaban, y como ese
handler solo despierta al loop del padre, `terminate()` no los mataba: el apagado
tardaba 10.5 s en vez de 8 y Docker lo habría cortado con SIGKILL. Lo encontré
midiendo el tiempo de salida y lo diagnostiqué con un volcado de stacks
(`faulthandler`). Se arregló con un `initializer` que en cada hijo pone SIGINT →
ignorar y SIGTERM → por defecto, el mismo criterio que en el TP1. Detalle en
notas.md, "Apagado ordenado (implementación)".

---

## 6. Limitaciones conocidas

- **Un hash ya arrancado no se corta**: el DELETE y el timeout cancelan el future
  de asyncio y la tarea queda `cancelada`/`fallida`, pero el proceso del pool
  **sigue calculando** hasta terminar y ocupa ese lugar. Solo se terminan los
  procesos al apagar, y para eso uso un atributo privado (`_pool._processes`);
  Python 3.14 agrega `terminate_workers()`.
- **El estado vive en memoria y nunca se purga**: el dict guarda todas las tareas,
  incluso las terminadas. Con el servidor andando mucho tiempo, crece sin límite.
- **El volcado no se reanuda**: al arrancar solo se reporta.
- **Una tarea cancelada estando pendiente sigue ocupando su lugar en la cola**
  hasta que un worker la saca y la saltea.
- **La métrica de ejecución incluye la espera en la cola del pool** de procesos
  (medición 3).
- **Un cliente httpx por tarea**: no reutiliza conexiones entre tareas, así que cada
  una paga DNS + TCP + TLS. Un cliente compartido con keep-alive sería más rápido.
- **Sin límite por servidor remoto**: muchas descargas al mismo host pueden recibir
  429. Se arreglaría con un `asyncio.Semaphore` por host.
- **Los campos de más se ignoran**: `{"segundos": 2, "texto": "x"}` en un `esperar`
  se acepta y `texto` se descarta.
- El nombre del volcado usa la hora del contenedor (UTC).

---

## 7. Lo que aprendí

Lo que aprendí en este TP fue cómo funciona un servidor asíncrono que atiende varios
clientes concurrentes en un solo hilo sin bloquear el event loop. También entendí
cómo se distribuye el trabajo entre workers, y me ayudó a entender la diferencia
entre concurrencia real y la secuencial. También me ayudó a entender cómo se ejecuta
cada tipo de tarea y por qué para hashear se manda a un ProcessPoolExecutor.

Hicimos mediciones en lugar de suponer: primero planteaba una hipótesis y después la
probábamos. Por ejemplo, en la segunda medición yo creía que los threads tardarían lo
mismo que la versión secuencial, pero terminaron tardando más del doble, porque el GIL
no solo serializa la ejecución sino que además hay un costo de tiempo por cada
traspaso entre hilos. O al medir el techo del pool, yo creía que el tiempo total iba a
ser el mismo con 1, 4 y 8 tareas de hashear porque mi computadora tiene 8 núcleos,
pero después de medir vimos que el tiempo empieza a subir con 8 tareas, porque en
realidad mi computadora tiene 4 núcleos físicos.

También este TP me sirvió para mejorar mi uso de agentes de IA. En el TP1 usé el tutor
de IA con Claude del navegador, no un agente: me sirvió para hacer el TP, pero siempre
le tenía que estar mandando los resultados de la terminal o los bugs que aparecían, y
también los archivos de clases anteriores, la consigna y el prompt del tutor por el
chat. Ahora, usando un agente, he podido ahorrar más tiempo al subir todo el contenido
necesario al repo, y no le tenía que mandar los resultados de la terminal ni los bugs
que aparecían, porque los podía ver él mismo. El uso de IA en este TP fue de la
siguiente manera: dividimos el TP en sesiones y cada día hacía una o dos. Al principio
de cada una repasábamos los conceptos de la sesión anterior; luego desarrollábamos el
código, donde yo (con ayuda del tutor) tomaba las decisiones de diseño; después el
tutor me hacía preguntas para asentar lo hecho, y la sesión terminaba repasando los
conceptos vistos y definiendo qué se iba a repasar en la próxima.

# TP1 — Monitor de Procesos y Threads

**Tomás Villar** · Computación II · Cohorte 2026

## Resultado: APROBADO

---

## Lo que hiciste bien

**`notas.md` es una bitácora genuina, y es lo que más valoro de tu entrega.**
Trescientas líneas de verificaciones empíricas. El caso que mejor lo muestra:
`notas.md:146-147`, donde establecés que un thread saturando un núcleo da 12.5%
en tu máquina de 8 cores, que `htop` usa la otra convención (100% = un núcleo), y
que lo **verificaste con un `while True:`**. Eso no sale de leer documentación:
sale de escribir un programa que quema CPU, mirar tu propio monitor y comparar.
Medir para decidir, en vez de suponer, es exactamente el hábito que este TP
quería instalar.

**Los índices de `/proc/<pid>/stat` los verificaste contra `/proc/self/stat`.**
`policy` en `resto[38]`, `rt_priority` en `resto[37]`, `priority`/`nice` en
`resto[15]`/`[16]`, `minflt`/`majflt` en `resto[7]`/`[9]`: todos correctos. Ese
archivo es una trampa — los campos se numeran desde 1 en el `man`, el nombre del
comando puede tener espacios y paréntesis, y basta un off-by-one para mostrar el
`nice` donde va el `priority` **sin que nada falle**. Usás `find('(')`/`rfind(')')`
para cortar el nombre, que es lo que evita el bug clásico, y después chequeaste
uno por uno.

**El `Value` es `'d'` y no `'i'`, con la razón escrita al lado.**
`main.py:96-105`: el comentario dice "'d' (double) y no 'i' porque
resumen/threads admiten intervalos de 0.5s". Es un detalle chico que delata que
leíste la tabla de la consigna y pensaste el tipo de dato en función del rango
que tiene que representar, en vez de poner `int` por costumbre. Y se lee dentro
del loop de cada analizador, así que `+`/`-` funciona en caliente y SIGHUP
también.

**Estado previo por thread con clave `"pid:tid"`, y sabés por qué.**
`threads.py:12` y `threads.py:33`. El comentario aclara que es para evitar
colisiones por reciclado de TIDs. Los TIDs se reusan cuando el contador del
kernel da la vuelta, y si tu diccionario de jiffies anteriores estuviera
indexado solo por TID, un thread nuevo heredaría el historial de uno muerto y te
daría un CPU% absurdo por una vuelta. Anticipaste un caso que casi nadie ve.

**Decodificación de máscaras bit a bit con fallback.**
`procfs.py:115-124`: recorrés los 64 bits y resolvés cada uno con
`signal.Signals(n).name`, cayendo a `SIG<N>` cuando no existe. Entendiste que
`SigBlk` es un entero donde el bit *n-1* representa la señal *n*, no una lista.

**El shutdown está razonado y el trade-off explicitado.**
Bandera `shared["seguir"]`, hijos con `SIG_IGN` en SIGINT, y `join()` sin
`terminate()`. Argumentás en el README por qué evitás `terminate()`: no querés
matar a un hijo a mitad de una escritura. Es un criterio defendible y está bien
que lo hayas escrito.

---

## Lo que falta, y el concepto detrás

**No existen el recolector ni el agregador, y eso es el hueco central.**
La arquitectura mínima obligatoria tenía cinco componentes; te faltan dos, y no
están fusionados en `main.py` tampoco: `main.py:107-116` lanza siete analizadores
y el display, punto. La consecuencia concreta y medible: `resumen.py:25`,
`memoria.py:14`, `fds.py:12`, `threads.py:18`, `senales.py:10`,
`scheduling.py:20` y `sistema.py:54` hacen **cada uno su propio
`os.listdir("/proc")`**, y varios reparsean los mismos archivos del mismo PID.
Con 400 procesos, eso es recorrer `/proc` siete veces en paralelo para obtener la
misma lista, y siete procesos compitiendo por el mismo I/O. El recolector existía
en la consigna para que ese trabajo se hiciera **una vez** y se repartiera.

Y el agregador faltante tiene un costo distinto: la consigna pedía un `ts` por
clave del snapshot, y no hay ninguno. Sin un proceso que consolide y selle
timestamps, no hay forma de saber si lo que estás viendo en la vista Señales es
de hace un segundo o de hace treinta. Un monitor sin marca de tiempo no puede
distinguir "el dato dice cero" de "el dato está viejo".

**No hay `Queue` ni `Pipe` en ningún lado.**
Busqué en todo tu `src/`: cero. Solo `Manager` + `Value`. La elección está
argumentada en el README, y `Manager` es legítimo para lo que hacés. Pero el TP
pedía explícitamente comunicar procesos con `Queue`, `Pipe` **y** memoria
compartida, porque cada una resuelve un patrón distinto: la `Queue` es la
primitiva del caso muchos-a-uno con encolado y backpressure, que es justo el que
tendrías si existiera el agregador. Al saltear esos dos componentes, te salteaste
también la mitad del temario de IPC.

**El padre hace polling con `sleep(0.5)` en vez de esperar.**
`main.py:122-123`: `while not cerrar: time.sleep(0.5)`. Funciona y el patrón de
bandera es async-signal-safe, así que no es incorrecto. Pero mirá el mecanismo:
cuando llega SIGUSR1, el handler prende la bandera e interrumpe el `sleep`, sí —
pero tu loop tiene que llegar a evaluar el `if`, y en el peor caso hay hasta
medio segundo de latencia entre la señal y el dump. Con un `select()` sobre un
self-pipe, el proceso está **dormido en el kernel** hasta que hay algo que leer y
reacciona en microsegundos, sin despertarse dos veces por segundo a preguntar si
pasó algo. La consigna mencionaba el self-pipe explícitamente y lo vimos en la
clase 6.

**El shutdown es frágil ante SIGTERM.**
Solo el padre registra SIGTERM y los hijos no lo ignoran (a diferencia de SIGINT,
que sí). Un `kill -TERM` al grupo de procesos los mata a todos por acción default
mientras el padre intenta cerrar ordenadamente. Y tu `join()` de `main.py:140`
no tiene `timeout` ni fallback: si un hijo se cuelga leyendo `/proc`, el monitor
queda esperando para siempre.

**Residuos de desarrollo que sugieren que no releíste antes de entregar.**
`display.py:479-480` y `482-483` hacen `erase()` y `getmaxyx()` **dos veces
seguidas**, literalmente duplicados. `fds.py:6` y `fds.py:8` registran
`SIG_IGN` para SIGUSR2 dos veces. Hay bloques de `print` de debug comentados en
seis de los siete analizadores, y `dibujar_placeholder` quedó muerta. Ninguna
rompe nada, pero juntas dicen que el código se escribió y no se volvió a leer
entero. En esa misma pasada habrías visto que el README raíz del repo todavía
declara "TP1 | Pendiente".

**Sin bonus de ningún tipo.**
La consigna ofrecía ocho extensiones y no tomaste ninguna, ni tests. Tu parseo
de `/proc` está entre los más cuidados del grupo: un par de tests sobre las
funciones de `procfs.py` con archivos de muestra te salían casi gratis, y habrían
dejado documentada la verificación de índices que ya hiciste a mano.

---

## Para la próxima

Una sola cosa: **escribí el recolector como proceso separado y que los siete
analizadores lean la lista de PIDs de ahí en vez de hacer cada uno su
`os.listdir("/proc")`.** Es el cambio que corrige el hueco arquitectónico
central, elimina siete recorridos redundantes por vuelta, y te obliga a resolver
el reparto —que es donde naturalmente aparece la `Queue` que hoy te falta.

---

## Cierre

Lo mejor de tu entrega es el método: `notas.md` muestra a alguien que verificó
sus suposiciones en vez de confiar en ellas, y la convención de CPU% comprobada
con un `while True:` es el ejemplo más claro de eso en todo el curso. Tu parseo
de `/proc` es técnicamente sólido, con los índices chequeados uno por uno y el
reciclado de TIDs anticipado. Lo que te faltó no fue rigor en lo que hiciste,
sino cobertura: dos de los cinco componentes obligatorios no se escribieron, y
con ellos quedó afuera la mitad del temario de IPC. Tenés el hábito difícil —
medir y verificar; falta completar la arquitectura sobre la que aplicarlo.
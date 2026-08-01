# Notas de diseño — TP1 Monitor de Procesos

## Docker / Infraestructura

**pid: host** → para ver los procesos del host (namespace de PIDs).

**privileged: true** → para leer los FDs de procesos ajenos del host.
SYS_PTRACE + DAC_READ_SEARCH no alcanzaban: el acceso a los symlinks de
/proc/<pid>/fd/ de otros procesos está protegido por varias capas a la vez
(capabilities + seccomp + LSM). privileged las desactiva todas juntas.
Trade-off: se resigna el aislamiento del contenedor, aceptable para un
monitor tipo htop que por naturaleza necesita ver todo el sistema.

**imagen Docker** → entorno reproducible (Python 3.11, dependencias, Linux garantizado).

Nota: durante el debugging bajé ptrace_scope a 0, pero con privileged NO hace
falta. Volver a 1 en el host (o se resetea al reiniciar).


## Parseo de /proc

**Parseo de /proc/<pid>/stat**: NO uso split() directo. El campo comm (nombre)
va entre paréntesis y puede tener espacios o paréntesis adentro (ej: "(sd-pam)").
Corto la línea en 3: antes del primer "(" = PID, entre "(" y el último ")" = comm,
después del ")" = resto (que sí es seguro para split). rfind(')') para el último ")".

**CPU%**: /proc no da un porcentaje, da jiffies acumulados (utime+stime desde que
nació el proceso). Calculo (delta_proceso / delta_sistema) * 100 entre dos
lecturas separadas por el intervalo. Leo /proc/stat UNA vez por vuelta (no una
por proceso). Primera aparición de un PID = 0% (no hay lectura anterior).


## Arquitectura / Concurrencia

**multiprocessing vs threading (GIL)**: usé multiprocessing y no threading porque
los analizadores hacen trabajo de CPU (parsear /proc), y el GIL impide que
múltiples threads ejecuten bytecode Python en paralelo. Con procesos separados,
cada uno tiene su propio intérprete y su propio GIL, logrando paralelismo real
sobre varios núcleos.

**Estado privado vs publicado**: el historial de jiffies anteriores es privado
del analizador (variable interna, NO va a memoria compartida). Solo el resultado
ya calculado (CPU%) se publica. Motivo: cada analizador maneja su propio cálculo;
los otros no necesitan verlo.

**Publicación atómica**: cada analizador arma su resultado en un dict LOCAL y lo
publica al Manager con UNA sola asignación (shared["resumen"] = resultado).
Evita que el display lea un estado a medio actualizar (race condition) y reduce
accesos al Manager (que son costosos).


## Limitaciones conocidas

**Shutdown**: al cortar con Ctrl-C, el hijo tira BrokenPipeError porque el padre
(dueño del Manager) muere primero y el hijo intenta escribir en un dict que ya
no existe. Falta shutdown limpio con señales (SIGINT/SIGTERM): el padre debe
avisar a los hijos y esperarlos con join antes de salir. → PENDIENTE

## Shutdown limpio (graceful)

El padre captura SIGINT/SIGTERM con un handler que solo levanta una bandera
(async-signal-safe). Los hijos IGNORAN SIGINT (SIG_IGN) para no morir solos y
quedar bajo control del padre.
El cierre NO usa terminate() (SIGTERM interrumpe al hijo en cualquier punto y se
enreda con el Manager). En su lugar: bandera compartida shared["seguir"]. El hijo
hace while shared["seguir"] y revisa cada vuelta; el padre baja la bandera y hace
join(). El hijo termina su vuelta actual y sale en un punto seguro.
Trade-off: el cierre puede tardar hasta un intervalo (el hijo termina su sleep),
pero muere ordenado en vez de a la mitad de una operación.

## Estructura de archivos
- procfs.py: helpers de parseo de /proc compartidos por todos los analizadores.
- resumen.py: el analizador de resumen (el hijo). No lanza procesos ni crea Manager.
- main.py: orquestador (el padre). Crea el Manager, lanza los procesos, maneja
  señales (SIGINT/SIGTERM) y el cierre ordenado.
Imports planos porque el entry point (main.py) se ejecuta desde src/, donde están
los tres. La subcarpeta analizadores/ queda pendiente para cuando haya varios.

## Memoria virtual (vista memoria)
VmSize = espacio de direcciones reservado/prometido (puede ser >> RAM física;
un navegador reserva ~1.2 TB virtuales). VmRSS = memoria realmente en RAM
(~419 MB). Para "cuánta RAM come de verdad" se usa VmRSS, no VmSize.
Los procesos de kernel (kthreads) no tienen campos Vm*: se usa .get(clave, '0 kB')
para no romper con KeyError.

## Orquestación multiproceso
main.py guarda los procesos en una LISTA. Patrón: for start() (lanzar todos),
luego for join() (esperar todos). Escalable: agregar un analizador = una línea
más en la lista, sin tocar la lógica.

## Page faults (vista memoria)
minor fault = página pedida ya estaba en RAM (caché, COW, lib ya cargada) -> rápido.
major fault = hay que traerla del DISCO (swap, ejecutable no cargado) -> lento.
Muchos major faults = proceso yendo a disco = señal de poca RAM/swapping.
Vienen de /proc/<pid>/stat campos 10 (minflt) y 12 (majflt). Contadores acumulados.

## Segmentos de /proc/<pid>/maps
Cada línea = una región de memoria virtual: rango (hex), permisos (r/w/x/p/s), etiqueta.
Clasificación por permisos y etiqueta, de lo específico a lo general:
[heap]/[stack] por etiqueta; luego 'x'->text (código), 's'->shared, 'w'->data.
El orden importa: heap/stack antes que permisos (heap es rw-p, caería en data);
'x' antes que 'w' (una región rwx es código, la x manda).
Tamaño de región = int(fin,16) - int(inicio,16) (direcciones en hexadecimal).

## Dockerfile actualizado
CMD pasó de smoke_test.py a main.py. COPY src/ ./src/ + WORKDIR /app/src para
que los imports funcionen parados en src/.

## Vista señales - decodificar máscaras de bits
SigBlk/SigIgn/SigCgt/SigPnd en /proc/<pid>/status son máscaras hex de 64 bits:
cada bit = una señal. Bit N-1 prendido = señal N está en el conjunto (ojo el
desfasaje: señales desde 1, bits desde 0).
Se lee un bit con AND: numero & (1 << (n-1)). El (1<<k) fabrica una máscara con
solo el bit k prendido; el & da distinto de cero si ese bit estaba en 1.
signal.Signals(n).name traduce número->nombre (try/except para números inválidos).
SIGKILL(9) y SIGSTOP(19) nunca se pueden bloquear/ignorar/capturar (imparables).
Los kthreads ignoran las 64; systemd captura varias con handlers propios.

## Vista FDs (file descriptors)
Un FD es un número que el kernel da por cada recurso abierto (archivo, socket,
pipe, terminal). 0=stdin, 1=stdout, 2=stderr siempre; de 3 en adelante los que
abre el proceso.
En /proc/<pid>/fd/ cada FD es un symlink; os.readlink() da su destino.
Tipo inferido por el prefijo del destino (startswith): socket:->socket,
pipe:->pipe, /dev/pts o /dev/tty ->tty, / ->file, resto->otro.
Orden: tty antes que file (/dev/pts también empieza con /).
Requiere privileged para leer FDs de procesos ajenos (igual que el maps).

## Vista threads (LWPs)
Los threads de un proceso viven en /proc/<pid>/task/<tid>/, cada uno con su
propio stat, status, comm (misma estructura que un proceso).
El thread principal tiene TID == PID. En Linux el PID es también el TGID
(Thread Group ID): todos los threads comparten TGID, cada uno tiene su TID único.
parsear_stat(pid, tid=None) reusa la misma función: sin tid abre /proc/<pid>/stat,
con tid abre /proc/<pid>/task/<tid>/stat. tid=None por defecto -> no rompe las
llamadas viejas.
Loop anidado: por cada pid, recorrer sus tids. Doble try/except (proceso y thread).
PENDIENTE: CPU% por thread (delta de jiffies por TID).

CPU% por thread: mismo mecanismo que el de procesos (delta de jiffies), pero
por cada TID. Clave del historial: f"{pid}:{tid}" (no solo tid, porque los TIDs
se reciclan y podrían colisionar en el tiempo con otro proceso).
Verificado: un proceso CPU-bound (while True) muestra su thread al ~100%;
la mayoría de threads dan 0% porque están dormidos (estado S), no es un bug.
Convención CPU%: 100% = todos los núcleos (delta_sistema suma los 8 cores).
Por eso un thread saturando 1 núcleo da 12.5% (1/8), no 100%. htop usa la otra
convención (100% = 1 núcleo). Verificado con while True: da 12.5% estable.

## Vista scheduling
- nice (-20 a +19, campo 19 stat): amabilidad. nice alto = cede CPU = menos prioridad.
  Por defecto 0 (heredado). Bajar el nice (más prioridad) requiere root.
- priority (campo 18 stat): representación interna del kernel = nice + 20 (0 a 39).
  Menor priority = MAYOR prioridad real.
- policy (campo 41 stat -> indice 38 en resto, NO 28): 0=OTHER (normal, respeta nice),
  1=FIFO / 2=RR (real-time, le ganan a todo lo normal). Real-time requiere privilegios
  porque un FIFO con bug puede secuestrar el sistema entero.
- context switches (status): voluntary = el proceso cede la CPU (espera I/O);
  nonvoluntary = el kernel se la arranca (se acabó su turno). CPU-bound -> muchos
  nonvoluntary; I/O-bound -> muchos voluntary.
- PGID/SID (campos 5/6 stat): jerarquía sesión > grupo > proceso.
- affinity: os.sched_getaffinity(pid) -> núcleos donde puede correr. Se convierte a
  list() porque los set no son serializables a JSON.
- OJO parseo: la fórmula indice=campo-3 vale, pero verificar SIEMPRE contra un campo
  con valor distintivo (no 0), porque dos ceros "coinciden" falsamente.

  ## Vista sistema (global)
A diferencia de los otros 6 (por proceso), este es GLOBAL: una sola foto, dict
PLANO {campo: valor}, sin loop de PIDs.
- /proc/uptime: segundos encendida (primer número). Convertir con // y % a h/m/s.
- /proc/meminfo (formato clave: valor kB como status): MemTotal, MemFree,
  MemAvailable (la que importa: libre + cachés liberables).
- /proc/loadavg: load a 1/5/15 min = promedio de procesos corriendo/esperando CPU.
  Comparar con nro de núcleos (load < núcleos = holgado). Si 1min > 15min = carga
  subiendo; si 1min < 15min = bajando.

  ## Display (TUI con curses)
El display es un proceso más, recibe shared por args, lee (no escribe).
Ignora SIGINT (lo maneja main), igual que los analizadores.
curses.wrapper(): entra a modo curses y RESTAURA la terminal al salir (aun con error).
curs_set(0): oculta cursor. timeout(200): getch espera 200ms y sigue -> refresca
sola sin quemar CPU (evita busy-wait) y sigue respondiendo al teclado.
Ciclo por vuelta: erase() -> dibujar -> refresh().
Evitar crash: getmaxyx() da alto/ancho; cortar filas con if fila >= alto-1: break,
y recortar texto con linea[:ancho-1]. Dibujar fuera de pantalla crashea curses.
shared.get("resumen", {}) con default para el arranque (analizador aun sin publicar).
Los analizadores YA NO imprimen: solo publican. El display es el unico que dibuja.

## TUI - 7 vistas completas
Una función dibujar_X por vista (separacion: analizadores publican, display dibuja).
Diccionario VISTAS {tecla: (nombre, clave)} para el cambio de vista (evita if/elif gigante).
Cada ficha lleva su propio comm -> cada vista es autosuficiente, el display NO toca /proc.
Vista sistema es distinta: global, dict plano, lineas fijas con formato (no tabla de procesos).
Patrones usados: .items() (clave+valor), ", ".join(...) (lista->string),
dict.get(k,0)+1 (contador), [:N] (muestra/limite), formato con //,% y kB->MB.

## Navegación (flechas + scroll)
seleccion = índice del proceso resaltado; offset = índice desde el que se dibuja.
keypad(True) para detectar KEY_UP/KEY_DOWN.
Límites estilo htop (frena en los extremos): encajar seleccion en [0, cantidad-1].
Scroll: si seleccion < offset -> offset baja; si seleccion >= offset+filas_visibles
-> offset sube. La ventana persigue a la selección.
Al dibujar: slice procesos[offset : offset+filas_visibles], y el resaltado usa
indice_real = offset + i (el i del enumerate es dentro de la tajada, no global).
curses.A_REVERSE resalta la fila seleccionada. Sistema no navega (es global).

## Pin + panel de detalle
pin_pid guarda el PID pineado (el PID, no el indice: el indice cambia al reordenarse).
Enter pinea el proceso seleccionado / despinea si ya habia.
ordenar_vista(vista, datos): fuente UNICA del orden, la usan el dibujo Y el Enter,
asi el indice 'seleccion' apunta al mismo PID en los dos lados.
Con pin: la lista usa la mitad de arriba (filas_visibles = alto//2 - 3), el panel
va desde alto//2. Sin pin: lista usa toda la pantalla.
dibujar_detalle junta info del PID desde varias vistas del shared (resumen+memoria+
scheduling) con doble .get() - NO toca /proc. Guarda: si el PID ya no esta (murio),
muestra "no disponible" en vez de crashear.

## Filtro por nombre (tecla /)
Dos modos: normal (teclas = comandos) y busqueda (teclas = texto). Variable
modo_busqueda distingue: sin ella, escribir "q" saldria del programa.
/ entra a modo busqueda; se acumulan caracteres con chr(tecla) (inverso de ord);
backspace = filtro[:-1]; Esc cancela/limpia; Enter confirma.
Solo se acumulan imprimibles (32 <= tecla <= 126).
El filtro se aplica despues de ordenar_vista, antes de dibujar:
list comprehension con filtro.lower() in comm.lower() (case-insensitive).
Al filtrar se resetea seleccion/offset (el indice viejo ya no vale).

## Filtro por usuario (tecla u)
Reusa el modo busqueda; tipo_filtro ("nombre"/"usuario") distingue como se aplica.
Nombre: 'in' (parcial) sobre comm. Usuario: '==' (exacto) sobre el primer campo
de Uid (info['Uid'].split()[0], el real UID).
LIMITACION CONOCIDA: el filtro por usuario funciona en las vistas que guardan Uid
en su ficha (resumen, memoria, senales, scheduling). fds y threads no parsean
status, asi que no incluyen Uid -> el filtro por usuario no aplica en esas dos.
Decision de diseno: no forzar parsear_status en fds/threads solo para el filtro.
Caso borde: fds y threads no tienen Uid en su ficha. El filtro por usuario usa
info.get('Uid') and filtro == info['Uid'].split()[0]: el short-circuit del 'and'
evita el IndexError (si no hay Uid, corta antes del .split()[0]). En esas vistas
el filtro por usuario da lista vacia en vez de crashear.

## Toggle de orden (tecla c): CPU% / RSS / PID
Variable global 'orden'. c rota cpu -> rss -> pid.
Diseño híbrido: si la vista tiene el campo del criterio, ordena por él (cpu en
resumen/threads, rss en memoria); si NO lo tiene, cae al ORDEN NATURAL de la vista
(no a PID), así ninguna vista se ve desordenada. pid ordena todas por PID.
Orden natural por vista: resumen=CPU, memoria=RSS, senales=#handlers, fds=#fds,
threads=maxCPU, scheduling=(priority,nice). Cumple la consigna (CPU%/RSS/PID).

## Docker: reconstruir con cambios
docker compose build --no-cache && docker compose run --rm monitor
El 'run' (no 'up') conecta el teclado a curses. --no-cache evita imagen vieja.
Dentro del contenedor (privileged) se leen TODOS los procesos incluidos root:
FDs de systemd (PID 1) visibles, orden por PID arranca en 1.

## Intervalos ajustables (+/-) con multiprocessing.Value
Value = memoria compartida para UN valor simple (Value('i', 2) = entero=2).
Mas liviano que Manager: acceso directo, sin proceso servidor intermediario.
Un Value por analizador, en un dict intervalos={"resumen": Value('i',2), ...}.
main crea el dict; a cada analizador le pasa SU value (args); al display le pasa
el dict ENTERO (toca el de la vista activa con +/-).
Analizador: time.sleep(intervalo.value) en vez de sleep fijo.
Display: +/- hace intervalos[vista].value +=/-= 1 (minimo 1s, si no busy-wait).
El cambio toma efecto en la proxima vuelta (el sleep en curso usa el valor viejo).
Defaults por vista segun cuan rapido cambia el dato: CPU 2s (rapido), señales/
scheduling 10s (casi estaticos). No releer datos estaticos seguido = eficiencia.
Manager (datos complejos) + Value (numeros simples) = herramienta adecuada por caso.
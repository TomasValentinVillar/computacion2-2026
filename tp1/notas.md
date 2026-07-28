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
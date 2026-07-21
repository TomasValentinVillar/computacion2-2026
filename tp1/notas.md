pid: host → para ver los procesos del host (namespace de PIDs)
privileged: true → para leer los FDs de procesos ajenos del host.
    SYS_PTRACE + DAC_READ_SEARCH no alcanzaban: el acceso a los symlinks de
    /proc/<pid>/fd/ de otros procesos está protegido por varias capas a la vez
    (capabilities + seccomp + LSM). privileged las desactiva todas juntas.
    Trade-off: se resigna el aislamiento del contenedor, aceptable para un
    monitor tipo htop que por naturaleza necesita ver todo el sistema.
imagen Docker → entorno reproducible (Python 3.11, dependencias, Linux garantizado)
Nota: durante el debugging bajé ptrace_scope a 0, pero con privileged NO hace
    falta. Volver a 1 en el host (o se resetea al reiniciar).
Parseo de /proc/<pid>/stat: NO uso split() directo. El campo comm (nombre)
va entre paréntesis y puede tener espacios o paréntesis adentro (ej: "(sd-pam)").
Corto la línea en 3: antes del primer "(" = PID, entre "(" y el último ")" = comm,
después del ")" = resto (que sí es seguro para split). rfind(')') para el último ")".
CPU%: /proc no da un porcentaje, da jiffies acumulados (utime+stime desde que
nació el proceso). Calculo (delta_proceso / delta_sistema) * 100 entre dos
lecturas separadas por el intervalo. Leo /proc/stat UNA vez por vuelta (no una
por proceso). Primera aparición de un PID = 0% (no hay lectura anterior).
El historial de jiffies anteriores es privado del analizador (variable interna,
NO va a memoria compartida). Solo el resultado ya calculado (CPU%) se publica.
Motivo: cada analizador maneja su propio cálculo; los otros no necesitan verlo.
# Informe Final del Proyecto - Simulador de Sistemas Operativos

## Resumen ejecutivo
El proyecto es un simulador educativo de gestión de procesos, planificación de CPU, memoria física, interrupciones y entrada/salida. El núcleo de simulación está implementado en C y la interfaz gráfica en Python con PySide6.

## Arquitectura
- C concentra la simulación: PCB, colas, CPU, memoria, interrupciones, E/S, Gantt y estadísticas.
- Python ejecuta el simulador C como subproceso y muestra el estado emitido por `SIM_DATA`.
- La GUI usa hilos Python para leer stdout/stderr sin bloquear la ventana.
- La comunicación se realiza con comandos por stdin y JSON por stdout.

## Componentes C
| Módulo | Responsabilidad |
| --- | --- |
| src/simulator/simulator_main.c | Punto de entrada del simulador C; inicializa el estado y procesa comandos. |
| src/simulator/simulator.c | Ciclo de vida global del simulador, creación y limpieza de estructuras. |
| src/simulator/input.c | Interpreta comandos: configuración, procesos manuales, procesos aleatorios, TEST, RUN, PAUSE y STOP. |
| src/simulator/process.c | Construcción de PCBs de usuario, procesos del SO, carga TEST, E/S e interrupciones planificadas. |
| src/simulator/process_table.c | Tabla principal de PCBs; mantiene la propiedad de las estructuras de proceso. |
| src/simulator/queue.c | Colas enlazadas para job, ready, dispositivos, no residentes y terminados. |
| src/simulator/scheduler.c | Planificadores FCFS, SJF, Round Robin y prioridad; variantes expropiativas y no expropiativas. |
| src/simulator/dispatcher.c | Despacho, guardado/restauración de contexto y costo de cambio de contexto. |
| src/simulator/cpu.c | Ejecución por ticks, avance de PC, quantum, interrupciones periódicas, E/S y errores. |
| src/simulator/memory.c | Gestión de memoria física con lista enlazada, bloques de 4 KB, segmentos y estrategias de asignación. |
| src/simulator/swap.c | Planificador de mediano plazo: descarga procesos bloqueados y reingresa procesos listos no residentes. |
| src/simulator/io.c | Colas por dispositivo, bloqueo por E/S y finalización de operaciones. |
| src/simulator/interrupt.c | Registro histórico y contadores de interrupciones por proceso y globales. |
| src/simulator/gantt.c | Construcción del diagrama de Gantt del CPU, inactividad y cambios de contexto. |
| src/simulator/protocol.c | Serialización JSON en líneas SIM_DATA para la interfaz Python. |
| src/simulator/names.c | Nombres legibles de algoritmos, estados, dispositivos, interrupciones y segmentos. |
| src/simulator/host_posix.c / host_windows.c | Funciones dependientes del sistema operativo para tiempo y espera. |

## Componentes Python
| Módulo | Responsabilidad |
| --- | --- |
| src/gui/main.py | Entrada de la interfaz PySide6. |
| src/gui/windows/* | Ventanas por algoritmo y ventana principal de selección. |
| src/gui/components/* | Controles visuales: entrada de procesos, mapa de memoria, Gantt, tablas, estadísticas y logs. |
| src/gui/services/simulation_service.py | Servicio de aplicación que coordina comandos, gateway, parser, reducer y estado de sesión. |
| src/gui/infrastructure/c_process_gateway.py | Ejecuta el binario C como subproceso y usa hilos Python para leer stdout/stderr sin bloquear la GUI. |
| src/gui/infrastructure/simulator_protocol_parser.py | Parsea líneas LOG y SIM_DATA emitidas por C. |
| src/gui/application/command_serializer.py | Convierte acciones de la GUI a comandos del simulador C. |
| src/gui/state/simulation_state_reducer.py | Actualiza el estado visible a partir de eventos completos del simulador. |
| src/gui/mappers/process_mapper.py | Mapea PCBs JSON a objetos UiProcess y conserva colores de visualización. |
| src/gui/domain/models.py | Modelos de datos de la interfaz y comandos de proceso. |

## Cumplimiento de requerimientos
| Requerimiento | Estado | Evidencia |
| --- | --- | --- |
| Estados NEW, READY, RUNNING, BLOCKED y TERMINATED | Cumplido | El PCB usa esos cinco estados visibles; además usa NONE como estado interno antes de la llegada. |
| PCB con identificador, estado, PC, SP y datos de planificación | Cumplido | El PCB guarda PID, estado, contexto CPU, memoria, datos de scheduler, E/S, interrupciones y errores. |
| Procesos del sistema operativo | Cumplido | Se crean Kernel, MemoryMgr, Scheduler, IOManager y Swapper con memoria reservada. |
| Colas de procesos | Cumplido | Existen job_q, ready_q, finished_q, nonresident_q y colas por dispositivo. |
| Planificación FCFS | Cumplido | Implementado en scheduler.c. |
| Planificación SJF | Cumplido | Implementado en variantes no expropiativa y expropiativa. |
| Planificación Round Robin | Cumplido | Implementado con quantum configurable y desalojo por temporizador. |
| Planificación por prioridad | Cumplido | Implementado en variantes no expropiativa y expropiativa; menor número significa mayor prioridad. |
| Dispatcher y cambio de contexto | Cumplido | El dispatcher aplica costo configurable, registra Gantt y guarda/restaura contexto. |
| Memoria con bloques de 4 KB | Cumplido | La memoria se modela como 1 GB físico dividido en frames de 4 KB. |
| First Fit, Best Fit y Worst Fit | Cumplido | Las tres estrategias seleccionan bloques libres desde la lista enlazada de memoria. |
| Segmentos de proceso | Cumplido | Se modelan TEXT, DATA, BSS, HEAP y STACK con porcentajes configurables para TEXT, DATA y memoria dinámica. |
| Planificador de largo plazo | Cumplido | Admite procesos desde job_q cuando llegaron y caben en memoria. |
| Planificador de mediano plazo | Cumplido parcial | Descarga procesos bloqueados residentes y reingresa READY no residentes; no desaloja READY/RUNNING como víctima. |
| Interrupciones | Cumplido | Se registran interrupciones de temporizador, syscall, solicitud y fin de E/S, y excepciones simuladas. |
| Dispositivos de E/S | Cumplido | La simulación usa teclado, disco e impresora para solicitudes aleatorias; la GUI muestra cinco colas de dispositivo. |
| Evento de teclado cancelar/continuar | Cumplido parcial | El teclado resuelve CONTINUE o CANCEL probabilísticamente; no depende de una tecla real del usuario. |
| Errores al 0.5 % | Cumplido | Cada proceso puede planificar un error fatal con probabilidad 0.5 %. |
| Carga de procesos manuales | Cumplido | La GUI y el comando ADD permiten nombre, memoria, burst, llegada, prioridad y segmentos. |
| Procesos aleatorios | Cumplido | RANDOM permite elegir entre 1 y 20 procesos; se fuerza cobertura mínima de E/S en cargas aleatorias grandes. |
| Prueba de 20 procesos | Cumplido | El comando TEST genera una carga determinística de 20 procesos. |
| Comparación de algoritmos | Cumplido | tools/compare_policies.py ejecuta matrices de planificación y memoria y genera un informe HTML. |
| Interfaz visual | Cumplido | PySide6 muestra Gantt, mapa de memoria, colas, PCB, procesos del SO, estadísticas y log. |

## Comparación base
Contexto: switch_cost=0.1, quantum=5, speed=100, seed=1234 y carga TEST de 20 procesos.

| Planificación | Memoria | Ready | TAT | Resp. | CPU % | Throughput | Frag. % | Waste MB | Swaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FCFS | First Fit | 110.60 | 147.91 | 70.86 | 98.6 | 0.0822 | 22.63 | 0.00 | 9 |
| FCFS | Best Fit | 110.60 | 147.91 | 70.86 | 98.6 | 0.0822 | 22.84 | 0.00 | 9 |
| FCFS | Worst Fit | 110.60 | 147.91 | 70.86 | 98.6 | 0.0822 | 26.50 | 0.00 | 10 |
| SJF no expropiativo | First Fit | 60.13 | 99.86 | 74.58 | 98.5 | 0.0859 | 54.35 | 0.00 | 12 |
| SJF no expropiativo | Best Fit | 60.41 | 100.31 | 74.17 | 98.5 | 0.0859 | 51.69 | 0.00 | 12 |
| SJF no expropiativo | Worst Fit | 60.33 | 100.31 | 74.17 | 98.5 | 0.0859 | 57.14 | 0.00 | 12 |
| SJF expropiativo | First Fit | 56.76 | 98.72 | 71.78 | 98.2 | 0.0815 | 54.49 | 0.00 | 12 |
| SJF expropiativo | Best Fit | 56.76 | 98.72 | 71.78 | 98.2 | 0.0815 | 54.23 | 0.00 | 12 |
| SJF expropiativo | Worst Fit | 56.76 | 98.72 | 71.78 | 98.2 | 0.0815 | 55.22 | 0.00 | 12 |
| Round Robin | First Fit | 101.78 | 158.63 | 56.40 | 97.1 | 0.0789 | 42.05 | 0.00 | 13 |
| Round Robin | Best Fit | 105.48 | 158.92 | 51.72 | 91.0 | 0.0794 | 43.85 | 0.00 | 13 |
| Round Robin | Worst Fit | 102.46 | 158.66 | 55.19 | 97.2 | 0.0790 | 44.73 | 0.00 | 12 |
| Prioridad no expropiativa | First Fit | 61.33 | 95.59 | 69.39 | 98.6 | 0.0849 | 52.68 | 0.00 | 11 |
| Prioridad no expropiativa | Best Fit | 61.33 | 95.59 | 69.39 | 98.6 | 0.0849 | 51.02 | 0.00 | 11 |
| Prioridad no expropiativa | Worst Fit | 61.33 | 95.59 | 69.39 | 98.6 | 0.0849 | 52.31 | 0.00 | 11 |
| Prioridad expropiativa | First Fit | 66.16 | 107.07 | 71.86 | 98.1 | 0.0798 | 55.18 | 0.00 | 11 |
| Prioridad expropiativa | Best Fit | 66.30 | 107.07 | 71.86 | 98.1 | 0.0798 | 56.29 | 0.00 | 11 |
| Prioridad expropiativa | Worst Fit | 66.16 | 107.07 | 71.86 | 98.1 | 0.0798 | 56.00 | 0.00 | 11 |

## Conclusión
La simulación cumple el objetivo central: modelar planificación, memoria, interrupciones, E/S y PCB con visualización. La separación C/Python permite probar el núcleo desde consola, usar la GUI para la demostración y ejecutar comparaciones reproducibles.

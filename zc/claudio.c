/*
 * FCFS Process Scheduler Simulator
 * Gestión de Procesos y Memoria — Algoritmo FCFS (Non-preemptive)
 *
 * Compile: gcc -o fcfs fcfs_simulator.c -lpthread
 * Run:     ./fcfs
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>
#include <pthread.h>
#include <time.h>
#include <stdarg.h>

/* ─────────────────────────────────────────────
 *  CONSTANTES
 * ───────────────────────────────────────────── */

#define MAX_NAME        32
#define MAX_LOG         512
#define LOG_LINES       20       /* líneas del log visible               */
#define TOTAL_MEMORY    4096     /* KB de memoria física simulada        */
#define BLOCK_SIZE      128      /* KB — tamaño de bloque (múltiplo 2^n) */
#define TICK_MS         100      /* ms por unidad de tiempo              */
#define ERROR_RATE      0.005    /* 0.5 % de procesos con error          */

/* ─────────────────────────────────────────────
 *  ENUMS
 * ───────────────────────────────────────────── */

typedef enum {
    NEW         = 0,
    READY       = 1,
    RUNNING     = 2,
    BLOCKED     = 3,
    TERMINATED  = 4,
    ERROR_STATE = 5
} ProcessState;

typedef enum {
    IO_KEYBOARD = 0,
    IO_DISK     = 1,
    IO_PRINTER  = 2
} IoDevice;

/* ─────────────────────────────────────────────
 *  ESTRUCTURAS DEL PCB
 * ───────────────────────────────────────────── */

typedef struct {
    int program_counter;
    int stack_pointer;
} CpuContext;

typedef struct {
    double arrival_time;
    double burst_time;
    double remaining_time;
    double start_time;      /* -1 = no iniciado  */
    double finish_time;     /* -1 = no terminado */
    double waiting_time;
    double turnaround_time;
    double response_time;
} SchedulerData;

typedef struct {
    int    required_kb;
    int    base_address;    /* dirección base física (KB)    */
    int    limit_address;   /* base + required_kb            */
    int    blocks_used;     /* cantidad de bloques asignados */
    int    waste_kb;        /* desperdicio interno           */
    bool   is_loaded;
} MemoryData;

typedef struct {
    bool   has_io;
    IoDevice device;
    double io_start_time;
    double io_duration;
    char   interrupt_code[16];
} IoData;

typedef struct {
    bool   has_error;
    char   error_code[16];
    char   error_desc[64];
} ErrorData;

typedef struct {
    char          name[MAX_NAME];
    int           pid;
    ProcessState  state;
    CpuContext    cpu_ctx;
    SchedulerData sched;
    MemoryData    mem;
    IoData        io;
    ErrorData     err;
    int           interrupt_count;   /* total de interrupciones asignadas */
    int           interrupts_done;   /* interrupciones ya ocurridas       */
    double        next_interrupt_at; /* próxima interrupción (unidad de tiempo) */
} Pcb;

/* ─────────────────────────────────────────────
 *  COLA GENÉRICA (lista enlazada simple)
 *  HEAD = próximo a salir (FIFO)
 *  TAIL = último ingresado
 *
 *   tail → [n-1] → [n-2] → ... → [0] = head → NULL
 * ───────────────────────────────────────────── */

typedef struct Node {
    Pcb          pcb;
    struct Node *next;  /* apunta hacia head */
} Node;

typedef struct {
    int   count;
    Node *head;   /* próximo a dequeue */
    Node *tail;   /* último enqueued   */
} Queue;

/* ─────────────────────────────────────────────
 *  MAPA DE BITS DE MEMORIA
 *  Un bit por bloque de BLOCK_SIZE KB
 * ───────────────────────────────────────────── */

#define TOTAL_BLOCKS    (TOTAL_MEMORY / BLOCK_SIZE)

typedef struct {
    bool   used[TOTAL_BLOCKS];
    int    owner_pid[TOTAL_BLOCKS];  /* qué proceso ocupa cada bloque */
    int    free_kb;
} MemoryMap;

/* ─────────────────────────────────────────────
 *  LOG DE EVENTOS
 * ───────────────────────────────────────────── */

typedef struct {
    char   lines[LOG_LINES][MAX_LOG];
    int    write_idx;   /* posición circular de escritura */
    int    count;       /* cuántas líneas válidas hay     */
} EventLog;

/* ─────────────────────────────────────────────
 *  SIMULADOR PRINCIPAL
 * ───────────────────────────────────────────── */

typedef struct {
    /* Colas */
    Queue        process_q;    /* procesos ingresados aún no en ready */
    Queue        ready_q;      /* cola de listos (FIFO = FCFS)        */
    Queue        io_q;         /* procesos bloqueados por E/S         */
    Queue        finished_q;   /* procesos terminados                 */

    /* Estado CPU */
    Pcb         *running;      /* proceso en ejecución (NULL = idle)  */
    bool         cpu_busy;

    /* Contextos guardados (dispatcher) */
    CpuContext  *saved_contexts;
    int         *saved_pids;
    int          ctx_count;

    /* Memoria */
    MemoryMap    mem_map;

    /* Tiempo */
    double       current_time;

    /* Identificadores */
    int          next_pid;
    int          total_created;  /* para calcular tasa de error */

    /* Log */
    EventLog     log;

    /* Estadísticas */
    int          terminated_count;
    int          error_count;
    double       total_waiting;
    double       total_turnaround;
    double       total_response;
    double       idle_time;

    /* Sincronización */
    pthread_mutex_t lock;
    bool         running_sim;    /* false = salir del loop            */
    bool         paused;

} Simulator;

/* ─────────────────────────────────────────────
 *  PROTOTIPOS
 * ───────────────────────────────────────────── */

/* Cola */
Queue   q_init(void);
bool    q_empty(const Queue *q);
void    q_enqueue(Queue *q, Pcb p);
Pcb     q_dequeue(Queue *q);
Pcb    *q_find(Queue *q, int pid);
void    q_update(Queue *q, int pid, Pcb updated);
void    q_free(Queue *q);

/* Memoria */
MemoryMap  mem_init(void);
bool       mem_alloc(MemoryMap *m, Pcb *p);
void       mem_free(MemoryMap *m, const Pcb *p);
int        mem_free_kb(const MemoryMap *m);

/* PCB */
Pcb  pcb_create(Simulator *s, const char *name, int mem_kb,
                double burst, double arrival);

/* Log */
void log_add(EventLog *l, const char *fmt, ...);

/* Dispatcher */
void  dispatch_save_ctx(Simulator *s, const Pcb *p);
Pcb  *dispatch_restore_ctx(Simulator *s, int pid);

/* Scheduler */
bool  sched_admit(Simulator *s);   /* NEW → READY                      */
Pcb   sched_fcfs(Simulator *s);    /* elige siguiente proceso de ready  */
void  sched_check_io(Simulator *s);/* desbloquear procesos con I/O listo */

/* Interrupciones */
bool  handle_interrupt(Simulator *s, Pcb *p);

/* Simulación */
void  sim_init(Simulator *s);
void  sim_tick(Simulator *s);
void  sim_run(Simulator *s);
void  sim_print(Simulator *s);
void  sim_stats(Simulator *s);

/* UI / Input */
void *input_thread(void *arg);
void  add_process_interactive(Simulator *s);
void  print_memory_map(const MemoryMap *m);

/* Utilidades */
const char *state_str(ProcessState s);
double      get_time_ms(void);
void        ms_sleep(int ms);

/* ═══════════════════════════════════════════════
 *  IMPLEMENTACIÓN — COLA
 * ═══════════════════════════════════════════════ */

Queue q_init(void) {
    Queue q;
    q.count = 0;
    q.head  = NULL;
    q.tail  = NULL;
    return q;
}

bool q_empty(const Queue *q) {
    return q->head == NULL;
}

/*
 * Encola al final (tail).  La cola crece hacia la derecha:
 *   head ← n0 ← n1 ← ... ← tail(nuevo)
 * Dequeue saca de head (FIFO).
 */
void q_enqueue(Queue *q, Pcb p) {
    Node *node = malloc(sizeof(Node));
    if (!node) { fprintf(stderr, "OOM en q_enqueue\n"); exit(1); }
    node->pcb  = p;
    node->next = NULL;

    if (q_empty(q)) {
        q->head = node;
        q->tail = node;
    } else {
        q->tail->next = node;
        q->tail       = node;
    }
    q->count++;
}

/* Extrae el nodo más antiguo (head). Precondición: !q_empty */
Pcb q_dequeue(Queue *q) {
    Node *old_head = q->head;
    Pcb   p        = old_head->pcb;
    q->head = old_head->next;
    if (q->head == NULL) q->tail = NULL;
    free(old_head);
    q->count--;
    return p;
}

/* Devuelve puntero al PCB dentro del nodo con ese pid (para modificar in-place) */
Pcb *q_find(Queue *q, int pid) {
    Node *cur = q->head;
    while (cur) {
        if (cur->pcb.pid == pid) return &cur->pcb;
        cur = cur->next;
    }
    return NULL;
}

/* Actualiza el PCB con ese pid en la cola */
void q_update(Queue *q, int pid, Pcb updated) {
    Node *cur = q->head;
    while (cur) {
        if (cur->pcb.pid == pid) { cur->pcb = updated; return; }
        cur = cur->next;
    }
}

void q_free(Queue *q) {
    while (!q_empty(q)) q_dequeue(q);
}

/* ═══════════════════════════════════════════════
 *  IMPLEMENTACIÓN — MEMORIA (MAPA DE BITS)
 * ═══════════════════════════════════════════════ */

MemoryMap mem_init(void) {
    MemoryMap m;
    for (int i = 0; i < TOTAL_BLOCKS; i++) {
        m.used[i]      = false;
        m.owner_pid[i] = -1;
    }
    m.free_kb = TOTAL_MEMORY;
    return m;
}

int mem_free_kb(const MemoryMap *m) {
    return m->free_kb;
}

/*
 * Asigna memoria contigua al proceso (First-Fit simplificado).
 * El proceso se carga EN SU TOTALIDAD antes de ejecutar (requisito).
 * Retorna true si se pudo asignar.
 */
bool mem_alloc(MemoryMap *m, Pcb *p) {
    /* Bloques necesarios (redondeado hacia arriba) */
    int blocks_needed = (p->mem.required_kb + BLOCK_SIZE - 1) / BLOCK_SIZE;

    /* Buscar bloques contiguos libres (First-Fit) */
    int start = -1, count = 0;
    for (int i = 0; i < TOTAL_BLOCKS; i++) {
        if (!m->used[i]) {
            if (count == 0) start = i;
            count++;
            if (count == blocks_needed) break;
        } else {
            start = -1; count = 0;
        }
    }

    if (count < blocks_needed) return false;  /* sin memoria */

    /* Marcar bloques */
    for (int i = start; i < start + blocks_needed; i++) {
        m->used[i]      = true;
        m->owner_pid[i] = p->pid;
    }

    p->mem.base_address = start * BLOCK_SIZE;
    p->mem.limit_address = p->mem.base_address + (blocks_needed * BLOCK_SIZE) - 1;
    p->mem.blocks_used   = blocks_needed;
    p->mem.waste_kb      = (blocks_needed * BLOCK_SIZE) - p->mem.required_kb;
    p->mem.is_loaded     = true;
    m->free_kb          -= blocks_needed * BLOCK_SIZE;

    return true;
}

void mem_free(MemoryMap *m, const Pcb *p) {
    for (int i = 0; i < TOTAL_BLOCKS; i++) {
        if (m->owner_pid[i] == p->pid) {
            m->used[i]      = false;
            m->owner_pid[i] = -1;
        }
    }
    m->free_kb += p->mem.blocks_used * BLOCK_SIZE;
}

/* ═══════════════════════════════════════════════
 *  IMPLEMENTACIÓN — LOG
 * ═══════════════════════════════════════════════ */

void log_add(EventLog *l, const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vsnprintf(l->lines[l->write_idx], MAX_LOG, fmt, args);
    va_end(args);
    l->write_idx = (l->write_idx + 1) % LOG_LINES;
    if (l->count < LOG_LINES) l->count++;
}

/* ═══════════════════════════════════════════════
 *  IMPLEMENTACIÓN — PCB
 * ═══════════════════════════════════════════════ */

Pcb pcb_create(Simulator *s, const char *name, int mem_kb,
               double burst, double arrival) {
    Pcb p;
    memset(&p, 0, sizeof(Pcb));

    strncpy(p.name, name, MAX_NAME - 1);
    p.pid   = s->next_pid++;
    p.state = NEW;

    /* CPU Context */
    p.cpu_ctx.program_counter = 0;
    p.cpu_ctx.stack_pointer   = 0;

    /* Scheduler data */
    p.sched.arrival_time   = arrival;
    p.sched.burst_time     = burst;
    p.sched.remaining_time = burst;
    p.sched.start_time     = -1.0;
    p.sched.finish_time    = -1.0;
    p.sched.waiting_time   = 0.0;
    p.sched.turnaround_time = 0.0;
    p.sched.response_time  = 0.0;

    /* Memoria */
    p.mem.required_kb  = mem_kb;
    p.mem.base_address = -1;
    p.mem.limit_address = -1;
    p.mem.blocks_used  = 0;
    p.mem.waste_kb     = 0;
    p.mem.is_loaded    = false;

    /* I/O — asignada aleatoriamente entre los dispositivos */
    p.io.has_io = (rand() % 2 == 0);   /* 50 % de procesos tienen E/S */
    if (p.io.has_io) {
        p.io.device        = (IoDevice)(rand() % 3);
        p.io.io_duration   = 1.0 + (rand() % 10);   /* entre 1 y 10 u.t. */
    }

    /* Interrupciones: entre 5 y 20, proporcional al burst */
    double factor = burst / 50.0;
    p.interrupt_count      = 5 + (int)(factor * 15);
    if (p.interrupt_count > 20) p.interrupt_count = 20;
    p.interrupts_done      = 0;
    /* Primera interrupción a burst * random[0.1, 0.9] */
    if (p.interrupt_count > 0)
        p.next_interrupt_at = burst * (0.1 + (rand() % 80) / 100.0);

    /* Error aleatorio (0.5 %) */
    p.err.has_error = ((double)rand() / RAND_MAX) < ERROR_RATE;
    if (p.err.has_error) {
        snprintf(p.err.error_code, 16, "ERR_%04d", p.pid);
        strncpy(p.err.error_desc, "Violación de segmento simulada", 63);
    }

    s->total_created++;
    return p;
}

/* ═══════════════════════════════════════════════
 *  IMPLEMENTACIÓN — DISPATCHER
 * ═══════════════════════════════════════════════ */

void dispatch_save_ctx(Simulator *s, const Pcb *p) {
    s->saved_contexts = realloc(s->saved_contexts,
                                sizeof(CpuContext) * (s->ctx_count + 1));
    s->saved_pids     = realloc(s->saved_pids,
                                sizeof(int) * (s->ctx_count + 1));
    if (!s->saved_contexts || !s->saved_pids) {
        fprintf(stderr, "OOM en dispatch_save_ctx\n"); exit(1);
    }
    s->saved_contexts[s->ctx_count] = p->cpu_ctx;
    s->saved_pids[s->ctx_count]     = p->pid;
    s->ctx_count++;
}

/* ═══════════════════════════════════════════════
 *  IMPLEMENTACIÓN — SCHEDULER / LÓGICA FCFS
 * ═══════════════════════════════════════════════ */

/*
 * Admite procesos de process_q a ready_q
 * si su arrival_time <= current_time Y hay memoria.
 */
bool sched_admit(Simulator *s) {
    bool admitted = false;
    /* Recorrer toda la process_q y admitir los que llegaron */
    Queue tmp = q_init();

    while (!q_empty(&s->process_q)) {
        Pcb p = q_dequeue(&s->process_q);
        if (p.sched.arrival_time <= s->current_time) {
            /* Intentar asignar memoria */
            if (mem_alloc(&s->mem_map, &p)) {
                p.state = READY;
                p.cpu_ctx.program_counter = p.mem.base_address;
                q_enqueue(&s->ready_q, p);
                log_add(&s->log,
                    "  [ADMIT] %s [PID %d] -> READY  Base=0x%04X  Mem=%dKB",
                    p.name, p.pid, p.mem.base_address, p.mem.required_kb);
                admitted = true;
            } else {
                /* Sin memoria: devolver a process_q */
                q_enqueue(&tmp, p);
                log_add(&s->log,
                    "  [MEM]   %s [PID %d] espera memoria libre (%dKB needed)",
                    p.name, p.pid, p.mem.required_kb);
            }
        } else {
            /* Aún no llegó */
            q_enqueue(&tmp, p);
        }
    }
    /* Devolver los que no se admitieron */
    while (!q_empty(&tmp)) {
        q_enqueue(&s->process_q, q_dequeue(&tmp));
    }
    return admitted;
}

/*
 * FCFS: retorna el primer proceso de ready_q.
 * Precondición: !q_empty(&ready_q)
 */
Pcb sched_fcfs(Simulator *s) {
    return q_dequeue(&s->ready_q);
}

/*
 * Revisa la cola de E/S y desbloquea procesos cuya
 * interrupción de E/S ya terminó.
 */
void sched_check_io(Simulator *s) {
    Queue tmp = q_init();
    while (!q_empty(&s->io_q)) {
        Pcb p = q_dequeue(&s->io_q);
        double io_end = p.io.io_start_time + p.io.io_duration;
        if (s->current_time >= io_end) {
            p.state = READY;
            q_enqueue(&s->ready_q, p);
            log_add(&s->log,
                "  [IO_END] %s [PID %d] E/S terminada -> READY",
                p.name, p.pid);
        } else {
            q_enqueue(&tmp, p);
        }
    }
    while (!q_empty(&tmp)) q_enqueue(&s->io_q, q_dequeue(&tmp));
}

/*
 * Maneja interrupciones del proceso en ejecución.
 * Devuelve true si el proceso fue bloqueado por E/S.
 */
bool handle_interrupt(Simulator *s, Pcb *p) {
    if (p->interrupts_done >= p->interrupt_count) return false;
    if (p->sched.burst_time - p->sched.remaining_time < p->next_interrupt_at)
        return false;

    p->interrupts_done++;

    /* Calcular tiempo hasta la próxima interrupción */
    if (p->interrupts_done < p->interrupt_count) {
        double step = p->sched.remaining_time /
                      (p->interrupt_count - p->interrupts_done + 1);
        p->next_interrupt_at = p->sched.burst_time
                             - p->sched.remaining_time + step;
    }

    /* Interrupción de E/S: bloquear proceso */
    if (p->io.has_io && (p->interrupts_done % 3 == 0)) {
        dispatch_save_ctx(s, p);
        p->state            = BLOCKED;
        p->io.io_start_time = (float)s->current_time;
        snprintf(p->io.interrupt_code, 16, "INT_IO_%d", p->interrupts_done);
        q_enqueue(&s->io_q, *p);

        const char *dev_names[] = {"Teclado", "Disco", "Impresora"};
        log_add(&s->log,
            "  [BLOCK] %s [PID %d] -> BLOCKED por %s (dur=%.1f u.t.)",
            p->name, p->pid,
            dev_names[p->io.device], p->io.io_duration);
        return true;
    }

    /* Interrupción de timer (sin bloqueo) */
    log_add(&s->log,
        "  [INT]   %s [PID %d] interrupcion #%d (TIMER)",
        p->name, p->pid, p->interrupts_done);
    return false;
}

/* ═══════════════════════════════════════════════
 *  TICK PRINCIPAL DE SIMULACIÓN
 * ═══════════════════════════════════════════════ */

void sim_tick(Simulator *s) {
    /* 1. Admitir procesos que llegaron */
    sched_admit(s);

    /* 2. Desbloquear procesos con E/S completa */
    sched_check_io(s);

    /* 3. Si la CPU está libre y hay procesos listos → despachar (FCFS) */
    if (!s->cpu_busy && !q_empty(&s->ready_q)) {
        Pcb next     = sched_fcfs(s);

        /* Primera vez que el proceso usa CPU */
        if (next.sched.start_time < 0) {
            next.sched.start_time   = s->current_time;
            next.sched.response_time = s->current_time - next.sched.arrival_time;
            next.sched.waiting_time  = next.sched.start_time - next.sched.arrival_time;
        }

        next.state   = RUNNING;
        next.cpu_ctx.program_counter = next.mem.base_address +
            (int)((next.sched.burst_time - next.sched.remaining_time) * 100);

        /* Guardar en heap (el running vive mientras ejecuta) */
        if (s->running) free(s->running);
        s->running   = malloc(sizeof(Pcb));
        *s->running  = next;
        s->cpu_busy  = true;

        log_add(&s->log,
            "  [RUN]   %s [PID %d] -> RUNNING  PC=0x%04X  Burst=%.1f",
            next.name, next.pid,
            next.cpu_ctx.program_counter,
            next.sched.burst_time);
    }

    /* 4. Avanzar el proceso en ejecución */
    if (s->cpu_busy && s->running) {
        Pcb *p = s->running;

        /* Verificar interrupción */
        bool blocked = handle_interrupt(s, p);
        if (blocked) {
            /* El proceso fue a io_q, liberar CPU */
            s->cpu_busy = false;
            free(s->running);
            s->running  = NULL;
            return;
        }

        /* Error: cancelar proceso (0.5 %) — solo si aún no ocurrió */
        if (p->err.has_error && p->sched.remaining_time < p->sched.burst_time * 0.5) {
            p->err.has_error = false;   /* disparar solo una vez */
            p->state         = ERROR_STATE;
            p->sched.finish_time = s->current_time;
            mem_free(&s->mem_map, p);
            q_enqueue(&s->finished_q, *p);
            s->error_count++;
            s->terminated_count++;
            log_add(&s->log,
                "  [ERROR] %s [PID %d] cancelado - %s: %s",
                p->name, p->pid, p->err.error_code, p->err.error_desc);
            s->cpu_busy = false;
            free(s->running);
            s->running  = NULL;
            return;
        }

        /* Avanzar un tick */
        double step = 1.0;   /* 1 unidad de tiempo por tick */
        p->sched.remaining_time -= step;
        p->cpu_ctx.program_counter += 100;
        p->cpu_ctx.stack_pointer   += 4;

        /* ¿Terminó? */
        if (p->sched.remaining_time <= 0.0) {
            p->sched.remaining_time  = 0.0;
            p->sched.finish_time     = s->current_time + step;
            p->sched.turnaround_time = p->sched.finish_time - p->sched.arrival_time;
            /* Si fue bloqueado y retomado, waiting ya fue calculado */
            if (p->sched.waiting_time == 0.0)
                p->sched.waiting_time = p->sched.turnaround_time - p->sched.burst_time;
            p->state = TERMINATED;

            /* Acumular estadísticas */
            s->total_waiting    += p->sched.waiting_time;
            s->total_turnaround += p->sched.turnaround_time;
            s->total_response   += p->sched.response_time;
            s->terminated_count++;

            /* Liberar memoria */
            mem_free(&s->mem_map, p);

            q_enqueue(&s->finished_q, *p);
            log_add(&s->log,
                "  [DONE]  %s [PID %d] TERMINADO  TAT=%.1f  Wait=%.1f  Resp=%.1f",
                p->name, p->pid,
                p->sched.turnaround_time,
                p->sched.waiting_time,
                p->sched.response_time);

            s->cpu_busy = false;
            free(s->running);
            s->running  = NULL;
        }
    } else if (!s->cpu_busy) {
        s->idle_time += 1.0;
    }

    /* 5. Actualizar tiempos de espera de procesos en ready */
    {
        Node *cur = s->ready_q.head;
        while (cur) {
            /* El tiempo de espera se calcula al final, no incrementalmente */
            cur = cur->next;
        }
    }

    s->current_time += 1.0;
}

/* ═══════════════════════════════════════════════
 *  RENDERIZADO EN TERMINAL
 * ═══════════════════════════════════════════════ */

static const char *io_device_str(IoDevice device) {
    switch (device) {
        case IO_KEYBOARD: return "Teclado";
        case IO_DISK:     return "Disco";
        case IO_PRINTER:  return "Impresora";
        default:          return "Desconocido";
    }
}

static void print_memory_map_basic(const MemoryMap *m) {
    printf("Memoria: %d KB libres de %d KB\n", mem_free_kb(m), TOTAL_MEMORY);
    printf("Bloques: ");
    for (int i = 0; i < TOTAL_BLOCKS; i++) {
        printf("%c", m->used[i] ? '#' : '.');
    }
    printf("\n");
}

static void print_process_line(const Pcb *p, double current_time) {
    printf("  PID=%d Nombre=%s Estado=%s Llegada=%.1f Burst=%.1f Restante=%.1f "
           "Mem=%dKB Base=%d PC=0x%04X Int=%d/%d",
           p->pid,
           p->name,
           state_str(p->state),
           p->sched.arrival_time,
           p->sched.burst_time,
           p->sched.remaining_time,
           p->mem.required_kb,
           p->mem.base_address,
           p->cpu_ctx.program_counter,
           p->interrupts_done,
           p->interrupt_count);

    if (p->state == BLOCKED && p->io.has_io) {
        double remaining_io = (p->io.io_start_time + p->io.io_duration)
                            - current_time;
        if (remaining_io < 0.0) remaining_io = 0.0;
        printf(" IO=%s IO_restante=%.1f", io_device_str(p->io.device),
               remaining_io);
    }

    printf("\n");
}

static void print_queue_basic(const char *title, const Queue *q,
                              double current_time) {
    printf("%s: %d proceso(s)\n", title, q->count);
    if (q_empty(q)) {
        printf("  (vacia)\n");
        return;
    }

    Node *cur = q->head;
    while (cur) {
        print_process_line(&cur->pcb, current_time);
        cur = cur->next;
    }
}

static void print_recent_log_basic(const EventLog *log) {
    int start = (log->count < LOG_LINES) ? 0 : log->write_idx;
    int shown = (log->count < 8) ? log->count : 8;

    printf("Log reciente: %d linea(s)\n", shown);
    if (shown == 0) {
        printf("  (sin eventos)\n");
        return;
    }

    for (int i = 0; i < shown; i++) {
        int idx = (start + (log->count < LOG_LINES
                            ? i
                            : (LOG_LINES - shown + i))) % LOG_LINES;
        printf("  %s\n", log->lines[idx]);
    }
}

void sim_print(Simulator *s) {
    printf("\n");
    printf("=== SIMULACION FCFS ===\n");
    printf("Tiempo: %.1f u.t.\n", s->current_time);
    printf("Estado: %s\n", s->paused ? "PAUSADA" : "EJECUTANDO");
    printf("Terminados: %d | Errores: %d | CPU idle: %.1f u.t.\n",
           s->terminated_count, s->error_count, s->idle_time);

    if (s->cpu_busy && s->running) {
        printf("CPU: ocupada\n");
        print_process_line(s->running, s->current_time);
    } else {
        printf("CPU: libre\n");
    }

    print_memory_map_basic(&s->mem_map);
    print_queue_basic("Cola READY", &s->ready_q, s->current_time);
    print_queue_basic("Cola IO", &s->io_q, s->current_time);
    print_queue_basic("Cola NEW/Pendientes", &s->process_q, s->current_time);
    print_queue_basic("Cola Finalizados", &s->finished_q, s->current_time);
    print_recent_log_basic(&s->log);
    printf("Controles: A=agregar | P=pausar/reanudar | Q=salir\n");
    printf("========================================\n");
    fflush(stdout);
}

/* ═══════════════════════════════════════════════
 *  ESTADÍSTICAS FINALES
 * ═══════════════════════════════════════════════ */

void sim_stats(Simulator *s) {
    printf("\n=== ESTADISTICAS FINALES FCFS ===\n");

    int n = s->terminated_count;
    if (n == 0) {
        printf("Sin procesos terminados.\n");
        return;
    }

    double avg_wt  = s->total_waiting    / n;
    double avg_tat = s->total_turnaround / n;
    double avg_rt  = s->total_response   / n;
    double cpu_util = (s->current_time > 0)
                    ? (1.0 - s->idle_time / s->current_time) * 100.0 : 0.0;
    double throughput = (s->current_time > 0)
                      ? (double)n / s->current_time : 0.0;

    printf("Procesos completados: %d\n", n);
    printf("Procesos con error: %d\n", s->error_count);
    printf("Tiempo total: %.1f u.t.\n", s->current_time);
    printf("Utilizacion CPU: %.1f%%\n", cpu_util);
    printf("Throughput: %.4f proc/u.t.\n", throughput);
    printf("Espera promedio: %.2f u.t.\n", avg_wt);
    printf("TAT promedio: %.2f u.t.\n", avg_tat);
    printf("Respuesta promedio: %.2f u.t.\n", avg_rt);

    printf("\nProcesos finalizados:\n");
    Node *cur = s->finished_q.head;
    while (cur) {
        Pcb *p = &cur->pcb;
        printf("PID=%d Nombre=%s Estado=%s Burst=%.1f Llegada=%.1f "
               "Inicio=%.1f Fin=%.1f Espera=%.1f TAT=%.1f Respuesta=%.1f\n",
               p->pid,
               p->name,
               state_str(p->state),
               p->sched.burst_time,
               p->sched.arrival_time,
               p->sched.start_time >= 0 ? p->sched.start_time : 0.0,
               p->sched.finish_time >= 0 ? p->sched.finish_time : 0.0,
               p->sched.waiting_time,
               p->sched.turnaround_time,
               p->sched.response_time);
        cur = cur->next;
    }

    printf("\nMapa de memoria final:\n");
    print_memory_map_basic(&s->mem_map);
    printf("========================================\n");
}

/* ═══════════════════════════════════════════════
 *  HILO DE INPUT (input no bloqueante)
 * ═══════════════════════════════════════════════ */

/*
 * Input_thread lee caracteres desde stdin.
 * Usamos terminal en modo raw para no bloquear el hilo de simulación.
 */

#include <termios.h>
#include <fcntl.h>

static struct termios orig_termios;

static void term_raw(void) {
    tcgetattr(STDIN_FILENO, &orig_termios);
    struct termios raw = orig_termios;
    raw.c_lflag &= ~(ECHO | ICANON);
    raw.c_cc[VMIN]  = 0;
    raw.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSANOW, &raw);
}

static void term_restore(void) {
    tcsetattr(STDIN_FILENO, TCSANOW, &orig_termios);
}

/* Buffer compartido para input del usuario */
typedef struct {
    Simulator *sim;
    bool       add_requested;
    bool       quit_requested;
    bool       pause_requested;
} InputCtx;

static InputCtx g_input_ctx;

void *input_thread(void *arg) {
    (void)arg;
    while (g_input_ctx.sim->running_sim) {
        char c = 0;
        read(STDIN_FILENO, &c, 1);
        if (c == 'a' || c == 'A') g_input_ctx.add_requested   = true;
        if (c == 'q' || c == 'Q') g_input_ctx.quit_requested  = true;
        if (c == 'p' || c == 'P') g_input_ctx.pause_requested = true;
        ms_sleep(20);
    }
    return NULL;
}

void add_process_interactive(Simulator *s) {
    /* Ir al final de la pantalla para el formulario */
    term_restore();
    printf("\n  -- Agregar Proceso --\n");

    char name[MAX_NAME]  = {0};
    char buf_burst[32]   = {0};
    char buf_mem[32]     = {0};
    char buf_arr[32]     = {0};

    printf("  Nombre     : "); fflush(stdout);
    fgets(name, MAX_NAME, stdin);
    int len = strlen(name);
    if (len > 0 && name[len-1] == '\n') name[len-1] = '\0';
    if (strlen(name) == 0) { term_raw(); return; }

    printf("  CPU Burst  : "); fflush(stdout);
    fgets(buf_burst, 32, stdin);
    double burst = atof(buf_burst);
    if (burst <= 0) burst = 10.0;

    printf("  Memoria(KB): "); fflush(stdout);
    fgets(buf_mem, 32, stdin);
    int mem = atoi(buf_mem);
    if (mem <= 0) mem = 128;

    printf("  Llegada(t) : "); fflush(stdout);
    fgets(buf_arr, 32, stdin);
    double arrival = atof(buf_arr);
    if (arrival < s->current_time) arrival = s->current_time;

    term_raw();

    pthread_mutex_lock(&s->lock);
    Pcb p = pcb_create(s, name, mem, burst, arrival);
    q_enqueue(&s->process_q, p);
    log_add(&s->log,
        "  [NEW]   %s [PID %d] ingresado  Burst=%.1f  Mem=%dKB  Arr=%.1f",
        p.name, p.pid, burst, mem, arrival);
    pthread_mutex_unlock(&s->lock);
}

/* ═══════════════════════════════════════════════
 *  INICIALIZACIÓN DEL SIMULADOR
 * ═══════════════════════════════════════════════ */

void sim_init(Simulator *s) {
    memset(s, 0, sizeof(Simulator));
    s->process_q      = q_init();
    s->ready_q        = q_init();
    s->io_q           = q_init();
    s->finished_q     = q_init();
    s->mem_map        = mem_init();
    s->running        = NULL;
    s->cpu_busy       = false;
    s->current_time   = 0.0;
    s->next_pid       = 1;
    s->total_created  = 0;
    s->running_sim    = true;
    s->paused         = false;
    s->saved_contexts = malloc(sizeof(CpuContext));
    s->saved_pids     = malloc(sizeof(int));
    s->ctx_count      = 0;
    memset(&s->log, 0, sizeof(EventLog));
    pthread_mutex_init(&s->lock, NULL);
    srand((unsigned)time(NULL));
}

void sim_free(Simulator *s) {
    q_free(&s->process_q);
    q_free(&s->ready_q);
    q_free(&s->io_q);
    q_free(&s->finished_q);
    free(s->saved_contexts);
    free(s->saved_pids);
    if (s->running) free(s->running);
    pthread_mutex_destroy(&s->lock);
}

/* ═══════════════════════════════════════════════
 *  LOOP PRINCIPAL
 * ═══════════════════════════════════════════════ */

void sim_run(Simulator *s) {
    while (s->running_sim) {
        /* Procesar peticiones de input */
        if (g_input_ctx.quit_requested) {
            s->running_sim = false;
            break;
        }
        if (g_input_ctx.pause_requested) {
            g_input_ctx.pause_requested = false;
            s->paused = !s->paused;
            log_add(&s->log, s->paused
                ? "  [SIM]   Simulacion PAUSADA"
                : "  [SIM]   Simulacion REANUDADA");
        }
        if (g_input_ctx.add_requested) {
            g_input_ctx.add_requested = false;
            add_process_interactive(s);
        }

        if (!s->paused) {
            pthread_mutex_lock(&s->lock);
            sim_tick(s);
            pthread_mutex_unlock(&s->lock);
        }

        sim_print(s);
        ms_sleep(TICK_MS);
    }
}

/* ═══════════════════════════════════════════════
 *  UTILIDADES
 * ═══════════════════════════════════════════════ */

const char *state_str(ProcessState st) {
    switch (st) {
        case NEW:         return "NEW";
        case READY:       return "READY";
        case RUNNING:     return "RUNNING";
        case BLOCKED:     return "BLOCKED";
        case TERMINATED:  return "TERMINATED";
        case ERROR_STATE: return "ERROR";
        default:          return "?";
    }
}

void ms_sleep(int ms) {
    struct timespec ts = { ms / 1000, (ms % 1000) * 1000000L };
    nanosleep(&ts, NULL);
}

/* ═══════════════════════════════════════════════
 *  MAIN
 * ═══════════════════════════════════════════════ */

int main(void) {
    Simulator sim;
    sim_init(&sim);

    /* Cargar procesos iniciales de ejemplo */
    printf("\n  FCFS Scheduler - Ingreso de procesos iniciales\n"
           "  Cuantos procesos desea ingresar? (0 = usar demo): ");
    fflush(stdout);

    char buf[32];
    fgets(buf, 32, stdin);
    int n = atoi(buf);

    if (n <= 0) {
        /* Demo con 5 procesos */
        const char *names[] = {"Alpha","Beta","Gamma","Delta","Epsilon"};
        double bursts[]     = {12, 5, 8, 17, 6};
        int    mems[]       = {256, 128, 512, 256, 128};
        double arrivals[]   = {0, 2, 4, 4, 8};
        for (int i = 0; i < 5; i++) {
            Pcb p = pcb_create(&sim, names[i], mems[i],
                               bursts[i], arrivals[i]);
            q_enqueue(&sim.process_q, p);
        }
        printf("  -> 5 procesos de demo cargados.\n");
    } else {
        for (int i = 0; i < n; i++) {
            char name[MAX_NAME];
            double burst, arrival;
            int mem;
            printf("\n  Proceso %d/%d\n", i + 1, n);
            printf("  Nombre     : "); fflush(stdout);
            fgets(name, MAX_NAME, stdin);
            int l = strlen(name);
            if (l > 0 && name[l-1] == '\n') name[l-1] = '\0';

            printf("  CPU Burst  : "); fflush(stdout);
            fgets(buf, 32, stdin); burst = atof(buf);
            if (burst <= 0) burst = 10;

            printf("  Memoria(KB): "); fflush(stdout);
            fgets(buf, 32, stdin); mem = atoi(buf);
            if (mem <= 0) mem = 128;

            printf("  Llegada(t) : "); fflush(stdout);
            fgets(buf, 32, stdin); arrival = atof(buf);

            Pcb p = pcb_create(&sim, name, mem, burst, arrival);
            q_enqueue(&sim.process_q, p);
        }
    }

    printf("\n  Iniciando simulacion en 2 segundos...\n");
    ms_sleep(2000);

    /* Arrancar hilo de input */
    g_input_ctx.sim              = &sim;
    g_input_ctx.add_requested   = false;
    g_input_ctx.quit_requested  = false;
    g_input_ctx.pause_requested = false;

    term_raw();
    pthread_t tid;
    pthread_create(&tid, NULL, input_thread, NULL);

    /* Loop principal */
    sim_run(&sim);

    /* Cleanup */
    term_restore();
    pthread_cancel(tid);
    pthread_join(tid, NULL);

    /* Mostrar estadísticas finales */
    sim_stats(&sim);
    sim_free(&sim);
    return 0;
}

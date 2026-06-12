#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <poll.h>

#define TICK		0.1	/* Cuanto avanza (u.t.) en cada iteracion */
#define TICK_US		50000	/* US = MICROSEGUNDOS, 1000 us = 1 ms */

#define TOTAL_BLOCKS	1024
#define BLOCK_SIZE      4    	/* Tamaño de cada bloque      */

#define ERR_CODE_MAX    16   	/* Máximo tamaño de codigo de error      */
#define ERR_DESC_MAX    32   	/* Máximo tamaño de descripción de error */

#define PCB_CANT	10

enum SimulatorState {
	SIM_RUN 	= 0,
	SIM_PAUSE	= 1,
	SIM_STOP	= 2,
};

enum AlgorithmSched {
	FCFS		= 0,
	NP_SJF		= 1,
	P_SJF		= 2,
	ROUND		= 3,
	NP_PRIOR	= 4,
	P_PRIOR		= 5
};

enum AlgorithmMem {
	FIRST	= 0,
	BEST 	= 1,
	WORST 	= 2
};

enum ProcessState {
	NEW         = 0,
	READY       = 1,
	RUNNING     = 2,
	BLOCKED     = 3,
	TERMINATED  = 4,
	ERROR_STATE = 5
};

enum IoDevice {
	IO_KEYBOARD = 0,
	IO_DISK     = 1,
	IO_PRINTER  = 2
};

enum IntType {
	/* Interrupciones de Hardware */
	INT_HW_IO           = 0,    /* I/O Devices        */
	INT_HW_TIMER        = 1,    /* Reloj del sistema  */
	
	/* Interrupciones de Software */
	INT_SW_SYSCALL      = 2,    /* Llamada al sistema */
	
	/* Excepciones */
	INT_EXC_DIV_ZERO    = 3,    /* Error división entre cero */
	INT_EXC_MEM         = 4     /* Error de acceso a memoria */
};

struct CpuContext {
	bool new;

	int program_counter;
	int stack_pointer;
};

struct SchedulerData {
	double arrival_time;
	double burst_time;
	double remaining_time;
	double start_time;
	double finish_time;
	double waiting_time;
	double turnaround_time;
	double response_time;
    
	int    priority;
	double remaining_quantum;
};

struct MemoryData {
	int  required_kb;
	int  assigned_blocks;
	int  waste_kb;

	int  start;
	int  limit;
};

struct IoData{
	bool	has_io;
	
	float	start_time;
	float	duration;
		
	enum IoDevice device;
};

struct Interrupt {
	int             int_count;
	int             int_done;
	double		next_int;
};

struct ErrorData {
	bool has_error;
	char error_code[ERR_CODE_MAX];
	char error_desc[ERR_DESC_MAX];
};

struct Pcb {
	char name[16];
	int pid;
	
	enum ProcessState	state;
	struct CpuContext	cpu_ctx;
	struct MemoryData	mem;
	struct SchedulerData	sched;
	struct IoData		io;
	struct ErrorData	err;
	
	struct Interrupt	interrupt;
};

struct Node {
	struct Pcb  *pcb;
	struct Node *next;
};

struct Queue {
	int cont;
	struct Node *head;
	struct Node *tail;
};

struct MemoryBlock {
	int start;
	int limit;
	int length;
	int owner;
	
	struct MemoryBlock *next;
};

struct MemoryBlockList {
	int cont;

	struct MemoryBlock *head;
	struct MemoryBlock *tail;
	
	struct MemoryBlock *max; /* Puntero al mayor espacio libre */
	int free;
};

struct GanttNode {
	int start;
	int limit;
	int owner;
	
	struct MemoryBlock *next;
};

struct GanttList {
	int cont;

	struct MemoryBlock *head;
};

struct ContextNode {
	int *pid;
	struct CpuContext ctx;
	
	struct ContextNode *next;
};

struct ContextList {
	int count;
	struct ContextNode *head;
};

struct Simulator {
	enum SimulatorState state;
	enum AlgorithmSched alg_sched;

	struct Queue created_processes;
	
	/* Scheduler largo plazo */
	struct Queue job_q;
	struct Queue ready_q;
	struct Queue io_q;
	struct Queue finished_q;
	
	/* Memoria */
	struct MemoryBlockList memory_list;
	enum AlgorithmMem alg_memory;
	
	/* Estado CPU */
	struct Pcb *running;
	bool cpu_busy;
	
	/* Dispatcher */
	struct ContextList context_list;
	struct Pcb *next_pcb;
	
	/* Diagrama de Gantt */
	struct GanttList gantt;
	
	/* Datos de simulación */
	double current_time;

	float quantum;	
	
	int next_pid;
};

/* Log */
void log_config(struct Simulator *);
void log_run();
void log_add(struct Pcb *);
void log_pause();
void log_stop();
/* Imprimir */
void print_pcb(struct Pcb *);
void print_queue(struct Queue *);
void print_memory(struct MemoryBlockList *);
void print_main_loop(struct Simulator *);
/* Iniciar */
struct Queue init_queue(void);
struct MemoryBlockList mem_init(void);
struct ContextList ctx_init(void);
struct GanttList gantt_init(void);
struct Simulator simulator_init(void);
/* Gestion colas */
void enqueue(struct Queue *, struct Pcb *);
struct Pcb *dequeue_last(struct Queue *);
struct Pcb *dequeue_head(struct Queue *);
struct Pcb *dequeue_tail(struct Queue *);
void dequeue_pcb(struct Queue *q, struct Pcb *p);
bool q_empty(struct Queue *);
void q_free(struct Queue *);
/* Gestion memoria */
bool allocate_block(struct MemoryBlockList *, struct MemoryBlock *, struct MemoryBlock *, struct Pcb *, const int);
bool kmalloc(struct Simulator *, struct Pcb *);
void kfree(struct MemoryBlockList *, struct Pcb *);
void kmerge(struct MemoryBlockList *);
void update_max_mem(struct MemoryBlockList *);
/* Dispatcher */
void dispatch(struct Simulator *);
void dispatch_save_ctx(struct Simulator *);
/* Long-Term Scheduler*/
void process_arrival(struct Simulator *);
void job_scheduler(struct Simulator *);
/* Short-Term Scheduler */
void scheduler(struct Simulator *);
struct Pcb *alg_fcfs(struct Simulator *);
struct Pcb *alg_np_sjf(struct Simulator *);
struct Pcb *alg_p_sjf(struct Simulator *);
/* Gestion de PCB */
struct Pcb create_pcb(struct Simulator *, char *, int, float, float, int);
/* Diagrama de Gantt */

/* Main loop */
void main_loop(struct Simulator *);
bool stdin_has_data(void);
void process_stdin(struct Simulator *, char *);

/* Log */
void log_config(struct Simulator *s)
{
	printf("Configuración aplicada.");
}

void log_run() 
{
	printf("Simulación iniciada.\n");
}

void log_add(struct Pcb *p)
{
	printf("Proceso %s(%d) agregado.\n", p->name, p->pid);
}

void log_pause()
{
	printf("Simulación pausada.\n");
}

void log_stop()
{
	printf("Simulación terminada.\n");
}

/* Imprimir */
void print_pcb(struct Pcb *p)
{
	printf("%-6s %-5d %-9d %-6.2f %-10.2f %-9.2f %-9d %-8d %-8d\n",
		p->name, p->pid, p->mem.required_kb, p->sched.burst_time, p->sched.remaining_time,
		p->sched.arrival_time, (p->mem.required_kb + BLOCK_SIZE - 1) / BLOCK_SIZE,
		p->mem.assigned_blocks, p->mem.waste_kb);
}

void print_queue(struct Queue *q)
{
	struct Node *tmp = q->head;
	
	while (tmp != NULL) {
		print_pcb(tmp->pcb);
		tmp = tmp->next;
	}
	
	free(tmp);
}

void print_memory(struct MemoryBlockList *m) {
	struct MemoryBlock *tmp = m->head;

	while (tmp != NULL) {
		printf("[%-4d) -> ", tmp->owner);
		tmp = tmp->next;
	}

	printf("NULL\n");

	tmp = m->head;

	while (tmp != NULL) {
		printf("%-10d", tmp->start);
		tmp = tmp->next;
	}

	printf("%d\n", TOTAL_BLOCKS);
}

void print_main_loop(struct Simulator *s)
{
	printf("\033[H\033[J");
		
	printf("\njob_q:\n");
	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
	print_queue(&s->job_q);
	
	printf("\nready_q:\n");
	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
	print_queue(&s->ready_q);
	
	printf("\nfinished_q:\n");
	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
	print_queue(&s->finished_q);
	
	printf("\nMemory list: (Free: %d)\n", s->memory_list.free);
	print_memory(&s->memory_list);
	
	printf("\nRunning: %s\n", s->running == NULL ? "false" : "true");
	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
	if (s->running != NULL)
		print_pcb(s->running);
	
	fflush(stdout);
}

/* Iniciar */
struct Queue init_queue(void)
{
	struct Queue q;
	
	q.cont = 0;
        q.head = NULL;
        q.tail = NULL;
	
	return q;
}

struct MemoryBlockList mem_init(void)
{
	struct MemoryBlockList m;
	struct MemoryBlock *mb = malloc(sizeof(struct MemoryBlock));
	
	if (!mb) {
		fprintf(stderr, "OOM en mem_init.\n");
		exit(1);
	}
	
	mb->start  = 0;
	mb->limit  = TOTAL_BLOCKS;
	mb->length = TOTAL_BLOCKS;
	mb->owner  = -1;
	mb->next   = NULL;
	
	m.cont = 1;
	m.head = mb;
	m.tail = mb;
	m.max  = mb;
	m.free = TOTAL_BLOCKS;
	
	return m;
}

struct ContextList ctx_init(void) // head -> cn -> ... -> c1 -> c0 -> NULL
{
	struct ContextList ctx;

	ctx.count = 0;
	ctx.head = NULL;

	return ctx;
}

struct GanttList gantt_init(void)
{
	struct GanttList g;

	g.cont = 0;
	g.head = NULL;

	return g;
}

struct Simulator simulator_init(void)
{
	struct Simulator s;

	s.state = SIM_RUN;

	s.created_processes = init_queue();
	
	s.job_q		= init_queue();
	s.ready_q	= init_queue();
	s.io_q		= init_queue();
	s.finished_q	= init_queue();
	
	s.memory_list	= mem_init();
	
	s.context_list	= ctx_init();
	
	s.gantt 	= gantt_init();

	s.running	= NULL;
	s.cpu_busy	= false;
	
	s.current_time	= 0;
	
	s.next_pid	= 0;

	return s;
}

/* Gestión de colas */
void enqueue(struct Queue *q, struct Pcb *p)	// Encola en head y crece hacia la derecha (tail)
{						// head -> p0 -> p1 -> p2 <- tail
	struct Node *node = malloc(sizeof(struct Node));
	
	if (!node) {
		fprintf(stderr, "OOM en create_node.\n");
		exit(1);
	}
	
	node->pcb = p;
	node->next = NULL;
	
	if (q_empty(q)) {
		q->tail = node;
		q->head = node;
	} else {
		q->tail->next = node;
		q->tail	= node;
	}
	
	q->cont++;
}

struct Pcb *dequeue_last(struct Queue *q)	// Se usa solo si q->cont == 1
{						// o sea queda UN solo elemento
	struct Node *tmp = q->head;
	struct Pcb *p = tmp->pcb;
	
	q->cont = 0;
	q->head = NULL;
	q->tail = NULL;
	
	free(tmp);
	
	return p;
}

struct Pcb *dequeue_head(struct Queue *q)
{
	if (q->cont == 1)
		return dequeue_last(q);
	
	struct Node *old_head = q->head;
	struct Pcb *p = old_head->pcb;
	
	q->head = q->head->next;
	q->cont--;
	
	free(old_head);
	
	return p;
}

struct Pcb *dequeue_tail(struct Queue *q)
{
	if (q->cont == 1)
		return dequeue_last(q);
	
	struct Node *old_tail = q->tail;
	struct Node *tmp = q->head;
	struct Pcb *p = old_tail->pcb;

	while (tmp->next != q->tail)
		tmp = tmp->next;
	
	tmp->next = NULL;
	q->tail = tmp;

	q->cont--;
	
	free(old_tail);
	
	return p;
}

void dequeue_pcb(struct Queue *q, struct Pcb *p) // Solo si p != NULL
{    
	struct Node *tmp_back;
	struct Node *tmp_pcb;
	int pid = p->pid;
	
	if (q->tail->pcb->pid == pid) {
		dequeue_tail(q);
		return;
	}
	
	if (q->head->pcb->pid == pid) {
		dequeue_head(q);
		return;
	}
	
	tmp_back = q->head;
	
	while (tmp_back->next->pcb->pid != pid)
		tmp_back = tmp_back->next;
	
	tmp_pcb = tmp_back->next;
	tmp_back->next = tmp_pcb->next;
	
	q->cont--;
	
	free(tmp_pcb);
}

bool q_empty(struct Queue *q)
{
    return q->tail == NULL;
}

void q_free(struct Queue *q)
{
	while(!q_empty(q)) {
		free(q->head->pcb);
		dequeue_head(q);
	}
}

/* Gestión de memoria */
bool allocate_block(struct MemoryBlockList *m,
		    struct MemoryBlock *curr,
		    struct MemoryBlock *ant,
		    struct Pcb *p,
		    const int blocks_needed)
{
	struct MemoryBlock *mb = malloc(sizeof(struct MemoryBlock));

	if (!mb) {
		fprintf(stderr, "OOM en allocate_block.\n");
		return false;
	}
	
	mb->start = curr->start;
	mb->limit = curr->start + blocks_needed;
	mb->length = blocks_needed;
	mb->owner = p->pid;
	mb->next = curr;
	
	if (ant != NULL) {
		ant->next = mb;
	} else {
		m->head = mb;
	}

	if (blocks_needed == curr->length) {
		mb->next = curr->next;

		if (m->tail == curr)
			m->tail = mb;

		free(curr);
	} else {
		mb->next = curr;

		curr->start = mb->limit;
		curr->length = curr->limit - curr->start;

		m->cont++;
	}

	/* Asignar valores en PCB */
	p->mem.start = mb->start;
	p->mem.limit = mb->limit;
	p->mem.assigned_blocks = blocks_needed;
	p->mem.waste_kb = blocks_needed * BLOCK_SIZE - p->mem.required_kb;
	
	m->free -= blocks_needed;
	update_max_mem(m);

	return true;
}

bool kmalloc(struct Simulator *s, struct Pcb *p)
{
	struct MemoryBlockList *m = &s->memory_list;
	struct MemoryBlock *tmp = m->head;		// Bloque libre donde se guarda el pcb
	struct MemoryBlock *tmp_ant = NULL;		// Bloque anterior a tmp, para conectar la lista
	enum AlgorithmMem alg = s->alg_memory;
	int blocks_needed = (p->mem.required_kb + BLOCK_SIZE - 1) / BLOCK_SIZE;

	if (blocks_needed > TOTAL_BLOCKS) {
		fprintf(stderr, "OOM en kmalloc: Proceso demasiado grande.");
		return false;
	}

	if (blocks_needed > m->max->length)
		return false;

	if (alg == FIRST) {
		while (tmp != NULL) {
			if (tmp->owner == -1 && blocks_needed <= tmp->length)
				return allocate_block(m, tmp, tmp_ant, p, blocks_needed);
			
			tmp_ant = tmp;
			tmp = tmp->next;
		}
	}
	
	if (alg == BEST) {
		struct MemoryBlock *best = NULL;
		struct MemoryBlock *best_ant = NULL;
		int min = s->memory_list.max->length;

		while (tmp != NULL) {
			if (tmp->owner == -1 && blocks_needed <= tmp->length && tmp->length <= min) {
				min = tmp->length;
			
				best_ant = tmp_ant;
				best = tmp;
			}

			tmp_ant = tmp;
			tmp = tmp->next;
		}

		return allocate_block(m, best, best_ant, p, blocks_needed);
	}

	if (alg == WORST) {
		struct MemoryBlock *worst = m->max;
		struct MemoryBlock *worst_ant = m->head;

		if (worst == m->head)
			return allocate_block(m, worst, NULL, p, blocks_needed);

		while (worst_ant->next != worst)
			worst_ant = worst_ant->next;

		return allocate_block(m, worst, worst_ant, p, blocks_needed);
	}

	return false;
}

void kfree(struct MemoryBlockList *m, struct Pcb *p)
{
	struct MemoryBlock *tmp = m->head;
	struct MemoryBlock *tmp_ant = NULL;

	while (tmp != NULL) {
		if (tmp->owner == p->pid) {
			tmp->owner = -1;
			m->free += tmp->length;
			
			update_max_mem(m);
			
			if ((tmp_ant != NULL && tmp_ant->owner == -1) || (tmp->next != NULL && tmp->next->owner == -1))
				kmerge(m);
			
			return;
		}
		
		tmp_ant = tmp;
		tmp = tmp->next;
	}
}

void kmerge(struct MemoryBlockList *m)
{
	struct MemoryBlock *tmp = m->head;

	while (tmp->next != NULL) {
		if (tmp->owner == -1 && tmp->next->owner == -1) {
			struct MemoryBlock *to_free = tmp->next;

			tmp->limit = tmp->next->limit;
			tmp->length = tmp->limit - tmp->start;
			tmp->next = to_free->next;

			if (to_free == m->tail)
				m->tail = tmp;

			free(to_free);

			m->cont--;
		} else {			// Importante no pasar a next, el
			tmp = tmp->next;	// siguiente hueco puede estar vacío
		}
	}

	update_max_mem(m);
}

void update_max_mem(struct MemoryBlockList *m)
{
	struct MemoryBlock *tmp = m->head;
	
	m->max = NULL;
	
	while (tmp != NULL) {
		if (tmp->owner == -1 && (m->max == NULL || tmp->length > m->max->length))
			m->max = tmp;
		
		tmp = tmp->next;
	}
}

/* Dispatcher */
void dispatch(struct Simulator *s)
{
	if (s->next_pcb == NULL)	// No hace falta creo
		return;
	
	dispatch_save_ctx(s);
	
	s->running = s->next_pcb;
	s->next_pcb = NULL;
	
	s->running->state = RUNNING;
	
	struct SchedulerData *sc = &s->running->sched;
	
	if (sc->start_time < 0) {
		sc->start_time = s->current_time;
		sc->response_time = sc->start_time - sc->arrival_time;
	}
	
	s->cpu_busy = true;
}

void dispatch_save_ctx(struct Simulator *s)	// Arreglar creo
{
	struct Pcb *p = s->running;
	struct ContextList *c = &s->context_list;
	struct ContextNode *cn;
	
	/* No hay contexto para guardar */
	if (p == NULL)
		return;

	/* Crear nodo de contexto */
	cn = malloc(sizeof(struct ContextNode));
	
	if (!cn) {
		fprintf(stderr, "OOM en save_ctx.\n");
		exit(1);
	}
	
	cn->ctx = p->cpu_ctx;
	cn->pid = &p->pid;

	/* Primer contexto guardado */
	if (c->count == 0) {
		c->head = cn;
		c->count++;
		return;
	}

	/* El contexto ya existe: se reemplaza */
	if (!p->cpu_ctx.new) {
		struct ContextNode *tmp = c->head;
		struct ContextNode *tmp_back = NULL;
		
		while (cn->pid != tmp->pid) {
			tmp_back = tmp;
			tmp = tmp->next;
		}

		if (tmp_back != NULL)
			tmp->next = cn;

		cn->next = tmp->next;

		free(tmp);

		return;
	}

	/* Contexto nuevo */
	cn->next = c->head;
	c->head = cn;
}

void terminate_running_process(struct Simulator *s)
{
	struct Pcb *p = s->running;
	
	if (p == NULL)		// No necesario creo
		return;
	
	struct SchedulerData *sc = &p->sched;
	
	sc->remaining_time = 0;
	sc->finish_time = s->current_time;
	sc->turnaround_time = sc->finish_time - sc->arrival_time;
	sc->waiting_time = sc->turnaround_time - sc->burst_time;

	p->state = TERMINATED;

	kfree(&s->memory_list, p);
	enqueue(&s->finished_q, p);

	s->running = NULL;
	s->cpu_busy = false;
}

/* Long-Term Scheduler */
void process_arrival(struct Simulator *s)	// Simula llegada a job_q
{	
	struct Queue *cq = &s->created_processes;
	struct Queue *jq = &s->job_q;
	struct Node *tmp = cq->head;

	while (tmp != NULL) {
		struct Pcb *p = tmp->pcb;

		tmp = tmp->next;

		if (p->sched.arrival_time <= s->current_time) {
			enqueue(jq, p);
			dequeue_pcb(cq, p);
		}
	}
}

void job_scheduler(struct Simulator *s)		// Long-Term Scheduler / Largo plazo
{						// Agarra procesos de job_q y 
	struct Queue *jq = &s->job_q;		// los mete a ready_q
	struct Queue *rq = &s->ready_q;
	struct Node *tmp = jq->head;

	while (tmp != NULL) {
		struct Pcb *p = tmp->pcb;
		
		tmp = tmp->next;
		
		/* Para procesos nuevos (NEW) */
		if (p->state == NEW && p->sched.arrival_time <= s->current_time) {
			if (!kmalloc(s, p))
				continue;

			p->state = READY;
			
			enqueue(rq, p);
			dequeue_pcb(jq, p);
		}
	}
}

/* Short-Term Scheduler*/
void scheduler(struct Simulator *s)
{
	struct Pcb *p = NULL;

	if (s->ready_q.cont == 0) {	// Adicional
		s->next_pcb = NULL;
		return;
	}

	switch (s->alg_sched) {
		case FCFS:
			p = alg_fcfs(s);
			s->next_pcb = p;
			break;

		case NP_SJF:
			p = alg_np_sjf(s);
			s->next_pcb = p;
			break;
		
		default:
			break;
	}
}

struct Pcb *alg_fcfs(struct Simulator *s)
{
	return dequeue_head(&(s->ready_q));
}

struct Pcb *alg_np_sjf(struct Simulator *s)	// Non-Preemptive Shortest Job First
{
	struct Queue *rq = &s->ready_q;
	struct Node *tmp = rq->head;
	struct Pcb *p = tmp->pcb;	/* Pcb con el menor tiempo restante (remaining_time) */

	tmp = tmp->next;
	while (tmp != NULL) {
		float tmp_time = tmp->pcb->sched.remaining_time;
		float min_time = p->sched.remaining_time;

		if (tmp_time < min_time)
			p = tmp->pcb;

		tmp = tmp->next;
	}

	dequeue_pcb(&s->ready_q, p);

	return p;
}

struct Pcb *alg_p_sjf(struct Simulator *s)	// Preemptive Shortest Job First
{	
	struct Queue *rq = &s->ready_q;
	struct Node *tmp = rq->head;
	struct Pcb *p = tmp->pcb;

	tmp = tmp->next;

	while (tmp != NULL) {

	}

	return p;
}

/* Gestion de PCB*/
struct Pcb create_pcb(struct Simulator *s, char *name, int mem_kb,
		      float burst, float arrival, int priority)
{
	struct Pcb p = {0};
	
	strcpy(p.name, name);
	
	p.pid   = s->next_pid++;
	p.state = NEW;
	
	/* CPU Context */
	p.cpu_ctx.new			= true;
	p.cpu_ctx.program_counter 	= 0;
	p.cpu_ctx.stack_pointer   	= 0;
	
	/* Scheduler Data */
	p.sched.arrival_time		= arrival;
	p.sched.burst_time		= burst;
	p.sched.remaining_time		= burst;
	p.sched.start_time		= -1.0;
	p.sched.finish_time		= -1.0;
	p.sched.waiting_time		=  0.0;
	p.sched.turnaround_time		=  0.0;
	p.sched.response_time		=  0.0;
	
	/* Memory Data */
	p.mem.required_kb		= mem_kb;
	p.mem.start			= -1;
	p.mem.limit			= -1;
	p.mem.assigned_blocks		=  0;
	p.mem.waste_kb			=  0;

	p.sched.priority 		= priority;
	p.sched.remaining_quantum	= s->quantum;

	/* I/O aleatorio entre los dispositivos */
	p.io.has_io = rand() % 2 == 0;  			/* la mitad de los procesos tienen I/O */
	p.io.start_time = burst * (0.1 + (rand() % 80) / 100.0);/* io entre el 10-90% del burst	*/
	p.io.duration	= -1;
	p.io.device 	= -1;
	
	if (p.io.has_io) {
		p.io.duration = 1.0 + (rand() % 10);  		/* entre 1 y 10 u.t. */
		p.io.device = (enum IoDevice)(rand() % 3);
	}
	/* 0.5% de los procesos presentan error */
	p.err.has_error = rand() % 200 == 0;

	if (p.err.has_error) {
		snprintf(p.err.error_code, sizeof(p.err.error_code), "ERR_%d", p.pid);
		snprintf(p.err.error_desc, sizeof(p.err.error_desc), "Error en el proceso %d", p.pid);
	}
	
	/* Interrupciones - entre 5 y 20, proporcional al burst y memoria */
	double factor = (burst / 100.0 + mem_kb / 1024.0) * 7.5; /* Rango: Burst 1-100 | Mem 1-1024 */
	p.interrupt.int_count     = 5 + (int)(factor);
		
	if (p.interrupt.int_count > 20)
		p.interrupt.int_count = 20;
		
	p.interrupt.int_done      = 0;
	p.interrupt.next_int      = burst * (0.1 + (rand() % 80) / 100.0); /* Primera interrupcion a 10-90 % del burst */
	
	return p;
}

/* Diagrama de Gantt */


/* Main loop */
void main_loop(struct Simulator *s)
{
	if (s->created_processes.cont > 0)			// Entran procesos a job_q
		process_arrival(s);				// segun arrival_time
	
	if (s->job_q.cont > 0)					// Si existen procesos no listos
		job_scheduler(s);				// se agregan a ready_q
	
	if (s->running == NULL && s->ready_q.cont > 0) {	// Cpu libre y procesos listos
		scheduler(s);
		dispatch(s);
	}
	
	if (s->running != NULL) {
		s->running->sched.remaining_time -= TICK;
		
		if (s->running->sched.remaining_time <= 0)	// Cpu ocupada y proceso terminado
			terminate_running_process(s);
	}
	
	if (s->created_processes.cont == 0 &&
	    s->job_q.cont == 0		   &&
	    s->ready_q.cont == 0	   &&
	    s->running == NULL)					// Se terminan todos los procesos
		s->state = SIM_STOP;				// y la CPU deja de trabajar

	/* Imprimir */
	print_main_loop(s);
}

bool stdin_has_data()
{
	struct pollfd fds;

	fds.fd = 0;		// stdin
	fds.events = POLLIN;	// revisar si existe algo

	int ret = poll(&fds, 1, 0);	// retorno = poll(fds, cant, t_espera)
	
	return (ret > 0 && (fds.revents & POLLIN));	// Ocurrió un evento POLLIN
}

void process_stdin(struct Simulator *s, char *line)
{
	if (strncmp(line, "CONFIG", 6) == 0) {
		int alg_sched, alg_mem;
		float quantum;

		sscanf(line, "CONFIG %d %d %f", &alg_sched, &alg_mem, &quantum);

		s->alg_sched 	= alg_sched;
		s->alg_memory 	= alg_mem;
		s->quantum 	= quantum;

		log_config(s);
	} else if (strncmp(line, "ADD", 3) == 0) {
		char name[32];
		float burst, arrival;
		int mem_kb, priority;

		sscanf(line, "ADD %31s %d %f %f %d",
			name, &mem_kb, &burst, &arrival, &priority);

		struct Pcb *p = malloc(sizeof(struct Pcb));

		*p = create_pcb(s, name, mem_kb, burst, arrival, priority);

		enqueue(&s->created_processes, p);

		log_add(p);
	} else if (strcmp(line, "RUN\n") == 0) {
		s->state = SIM_RUN;
		log_run();
	} else if (strcmp(line, "PAUSE\n") == 0) {
		s->state = SIM_PAUSE;
		log_pause();
	} else if (strcmp(line, "STOP\n") == 0) {
		s->state = SIM_STOP;
		log_stop();
	}
}

int main(void)
{
	struct Simulator simulator = simulator_init();
	struct Simulator *s = &simulator;
	char line[256];

	srand(time(NULL));

	for (int i = 0; i < PCB_CANT; i++) {
		float burst_time	= 1 + rand() % 9;
		float arrival_time	= 0;// + rand() % 9;
		int memory		= 512 + rand() % 1023;
		char name[3];
		
		snprintf(name, sizeof(name), "P%d", i);

		struct Pcb *pcb = malloc(sizeof(struct Pcb));
		*pcb = create_pcb(s, name, memory, burst_time, arrival_time, -1);
		
		enqueue(&s->created_processes, pcb);
	}

	setvbuf(stdout, NULL, _IOLBF, 0); /* stdout sale linea por linea (como un printf creo) */

	s->alg_memory = FIRST;
	s->alg_sched = FCFS;
	s->state = SIM_RUN;

	//printf("\033[?25l");
	while (s->state != SIM_STOP) {
		usleep(TICK_US);
		s->current_time += TICK;
		
		if (stdin_has_data()) {
			fgets(line, sizeof(line), stdin);
			process_stdin(s, line);
		}
		
		if (s->state == SIM_PAUSE)
			continue;

		main_loop(s);
	}
	printf("\033[?25h");

	q_free(&s->finished_q);

	return 0;
}
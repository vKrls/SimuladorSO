#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#define TICK		0.001	/* Cuanto avanza (u.t.) en cada iteracion */
#define TICK_US		250	/* US = MICROSEGUNDOS, 1000 us = 1 ms */
#define TIME_EPSILON	1e-9

#define TOTAL_BLOCKS	1024	/* bloquecitos de memoria */
#define BLOCK_SIZE      4    	/* Tamaño de cada bloque */

#define ERR_CODE_MAX    16   	/* Máximo tamaño de codigo de error */
#define ERR_DESC_MAX    32   	/* Máximo tamaño de descripción de error */

#define RANDOM_PROCESS_COUNT 5

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
	IO_NONE     = -1,
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
	bool new;	/* Saber si crear o actualizar */

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
	int required_kb;
	int assigned_blocks;
	int waste_kb;

	int start;
	int limit;
};

struct IoData{
	bool	has_io;

	float	start_time;
	float	duration;

	enum IoDevice device;
};

struct Interrupt {
	int		int_count;
	int		int_done;
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
	struct Pcb *pcb;
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
	double start;
	double limit;
	int owner;
	char name[16];

	struct GanttNode *next;
};

struct GanttList {
	int cont;

	struct GanttNode *head;
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

	/* Cosas de interrupciones, i/o, etc (zzz) */
	enum IntType interrupt_q;
	
	/* Memoria */
	struct MemoryBlockList memory_list;
	enum AlgorithmMem alg_memory;
	
	/* Estado CPU */
	struct Pcb *running;
	bool cpu_busy;
	
	/* Dispatcher */
	struct ContextList context_list;
	struct Pcb *next_pcb;
	
	double quantum;

	/* Diagrama de Gantt */
	struct GanttList gantt;
	
	/* Datos de simulación */
	double current_time;

	int sim_speed;

	int next_pid;
};

/* Log */
void log_config(struct Simulator *);
void log_run(void);
void log_add(struct Pcb *);
void log_pause(void);
void log_stop(void);
/* Imprimir - Deprecated */
void print_pcb(struct Pcb *);
void print_queue(struct Queue *);
void print_memory(struct MemoryBlockList *);
void print_main_loop(struct Simulator *);
/* Enviar datos a Python */
const char *process_state_name(enum ProcessState);
const char *io_device_name(enum IoDevice);
void send_json_string(const char *);
void send_pcb_data(struct Pcb *);
void send_queue_data(const char *, struct Queue *);
void send_memory_data(struct MemoryBlockList *);
void send_running_data(struct Pcb *);
void send_gantt_data(struct Simulator *);
void send_data(struct Simulator *);
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
struct Pcb *alg_sjf(struct Simulator *);
struct Pcb *alg_priority(struct Simulator *);
/* Gestion de PCB */
struct Pcb create_pcb(struct Simulator *, char *, int, double, double, int);
void create_random_processes(struct Simulator *);
/* Diagrama de Gantt */

/* Maquina de estados */
void set_process_state(struct Simulator *, struct Pcb *, enum ProcessState);
/* Main loop */
void sleep_microseconds(unsigned int);
bool stdin_has_data(void);
void process_stdin(struct Simulator *, char *);
bool should_preempt(struct Simulator *);
void tick_running_process(struct Simulator *);
void main_loop(struct Simulator *);

/* Log */
void log_config(struct Simulator *s)
{
	printf("Configuración aplicada: planificador=%d, memoria=%d, quantum=%.3f.\n",
		s->alg_sched, s->alg_memory, s->quantum);
}

void log_run(void)
{
	printf("Simulación iniciada.\n");
}

void log_add(struct Pcb *p)
{
	printf("Proceso %s(%d) agregado.\n", p->name, p->pid);
}

void log_pause(void)
{
	printf("Simulación pausada.\n");
}

void log_stop(void)
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

/* Deprecated */
// void print_main_loop(struct Simulator *s)
// {
// 	printf("\033[H\033[J");
		
// 	printf("\njob_q:\n");
// 	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
// 	print_queue(&s->job_q);
	
// 	printf("\nready_q:\n");
// 	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
// 	print_queue(&s->ready_q);
	
// 	printf("\nfinished_q:\n");
// 	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
// 	print_queue(&s->finished_q);
	
// 	printf("\nMemory list: (Free: %d)\n", s->memory_list.free);
// 	print_memory(&s->memory_list);
	
// 	printf("\nRunning: %s\n", s->running == NULL ? "false" : "true");
// 	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
// 	if (s->running != NULL)
// 		print_pcb(s->running);
	
// 	fflush(stdout);
// }

const char *process_state_name(enum ProcessState state)
{
	switch (state) {
		case NEW:         return "NEW";
		case READY:       return "READY";
		case RUNNING:     return "RUNNING";
		case BLOCKED:     return "BLOCKED";
		case TERMINATED:  return "TERMINATED";
		case ERROR_STATE: return "ERROR";
		default:          return "UNKNOWN";
	}
}

const char *io_device_name(enum IoDevice device)
{
	switch (device) {
		case IO_NONE:     return "NONE";
		case IO_KEYBOARD: return "KEYBOARD";
		case IO_DISK:     return "DISK";
		case IO_PRINTER:  return "PRINTER";
		default:          return "NONE";
	}
}

void send_json_string(const char *text)
{
	const unsigned char *c = (const unsigned char *)text;

	putchar('"');
	while (*c != '\0') {
		switch (*c) {
			case '"':  fputs("\\\"", stdout); break;
			case '\\': fputs("\\\\", stdout); break;
			case '\n': fputs("\\n", stdout);  break;
			case '\r': fputs("\\r", stdout);  break;
			case '\t': fputs("\\t", stdout);  break;
			default:
				if (*c < 0x20)
					printf("\\u%04x", *c);
				else
					putchar(*c);
		}
		c++;
	}
	putchar('"');
}

void send_pcb_data(struct Pcb *p)	/* Locura locura */
{
	printf("{\"pid\":%d,\"name\":", p->pid);
	send_json_string(p->name);
	printf(",\"state\":");
	send_json_string(process_state_name(p->state));
	printf(",\"cpu\":{\"program_counter\":%d,\"stack_pointer\":%d}",
		p->cpu_ctx.program_counter, p->cpu_ctx.stack_pointer);
	printf(",\"scheduler\":{\"arrival_time\":%.3f,\"burst_time\":%.3f,"
		"\"remaining_time\":%.3f,\"start_time\":%.3f,\"finish_time\":%.3f,"
		"\"waiting_time\":%.3f,\"turnaround_time\":%.3f,\"response_time\":%.3f,"
		"\"priority\":%d,\"remaining_quantum\":%.3f}",
		p->sched.arrival_time, p->sched.burst_time, p->sched.remaining_time,
		p->sched.start_time, p->sched.finish_time, p->sched.waiting_time,
		p->sched.turnaround_time, p->sched.response_time, p->sched.priority,
		p->sched.remaining_quantum);
	printf(",\"memory\":{\"required_kb\":%d,\"assigned_blocks\":%d,"
		"\"waste_kb\":%d,\"start_block\":%d,\"limit_block\":%d}",
		p->mem.required_kb, p->mem.assigned_blocks, p->mem.waste_kb,
		p->mem.start, p->mem.limit);
	printf(",\"io\":{\"has_io\":%s,\"start_time\":%.3f,\"duration\":%.3f,"
		"\"device\":", p->io.has_io ? "true" : "false",
		p->io.start_time, p->io.duration);
	send_json_string(io_device_name(p->io.device));
	printf("},\"interrupts\":{\"total\":%d,\"completed\":%d,\"next_time\":%.3f}",
		p->interrupt.int_count, p->interrupt.int_done, p->interrupt.next_int);
	printf(",\"error\":{\"has_error\":%s,\"code\":",
		p->err.has_error ? "true" : "false");
	send_json_string(p->err.error_code);
	printf(",\"description\":");
	send_json_string(p->err.error_desc);
	putchar('}');
	putchar('}');
}

void send_queue_data(const char *name, struct Queue *q)
{
	struct Node *node = q->head;
	bool first = true;

	printf("SIM_DATA {\"type\":\"queue\",\"name\":");
	send_json_string(name);
	printf(",\"count\":%d,\"processes\":[", q->cont);
	while (node != NULL) {
		if (!first)
			putchar(',');
		send_pcb_data(node->pcb);
		first = false;
		node = node->next;
	}
	printf("]}\n");
}

void send_memory_data(struct MemoryBlockList *memory)
{
	struct MemoryBlock *block = memory->head;
	bool first = true;

	printf("SIM_DATA {\"type\":\"memory\",\"total_blocks\":%d,"
		"\"block_size_kb\":%d,\"free_blocks\":%d,\"blocks\":[",
		TOTAL_BLOCKS, BLOCK_SIZE, memory->free);
	while (block != NULL) {
		if (!first)
			putchar(',');
		printf("{\"start_block\":%d,\"limit_block\":%d,\"length_blocks\":%d,"
			"\"owner_pid\":%d}", block->start, block->limit,
			block->length, block->owner);
		first = false;
		block = block->next;
	}
	printf("]}\n");
}

void send_running_data(struct Pcb *running)
{
	printf("SIM_DATA {\"type\":\"running\",\"process\":");
	if (running == NULL)
		printf("null");
	else
		send_pcb_data(running);
	printf("}\n");
}

void send_gantt_nodes(struct GanttNode *node, bool *first)
{
	if (node == NULL)
		return;

	/* La lista guarda el segmento más reciente en head. */
	send_gantt_nodes(node->next, first);

	if (!*first)
		putchar(',');

	printf("{\"pid\":%d,\"name\":", node->owner);
	send_json_string(node->name);
	printf(",\"start\":%.3f,\"limit\":%.3f,\"duration\":%.3f}",
		node->start, node->limit, node->limit - node->start);
	*first = false;
}

void send_gantt_data(struct Simulator *s)
{
	bool first = true;

	printf("SIM_DATA {\"type\":\"gantt\",\"current_time\":%.3f,"
		"\"count\":%d,\"segments\":[", s->current_time, s->gantt.cont);
	send_gantt_nodes(s->gantt.head, &first);
	printf("]}\n");
}

void send_data(struct Simulator *s)
{
	printf("SIM_DATA {\"type\":\"snapshot\",\"current_time\":%.3f,"
		"\"simulator_state\":%d,\"scheduler_algorithm\":%d,"
		"\"memory_algorithm\":%d,\"cpu_busy\":%s,\"quantum\":%.3f}\n",
		s->current_time, s->state, s->alg_sched, s->alg_memory,
		s->cpu_busy ? "true" : "false", s->quantum);
	send_queue_data("created_processes", &s->created_processes);
	send_queue_data("job_q", &s->job_q);
	send_queue_data("ready_q", &s->ready_q);
	send_queue_data("io_q", &s->io_q);
	send_queue_data("finished_q", &s->finished_q);
	send_running_data(s->running);
	send_memory_data(&s->memory_list);
	send_gantt_data(s);
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
	struct Simulator s = {0};

	s.state = SIM_PAUSE;
	s.alg_sched = FCFS;
	s.alg_memory = FIRST;
	s.quantum = 1.0f;

	s.created_processes = init_queue();
	
	s.job_q		= init_queue();
	s.ready_q	= init_queue();
	s.io_q		= init_queue();
	s.finished_q	= init_queue();
	
	s.memory_list	= mem_init();
	
	s.context_list	= ctx_init();
	
	s.gantt 	= gantt_init();

	s.running	= NULL;
	s.next_pcb	= NULL;
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
		struct Pcb *p = dequeue_head(q);
		free(p);
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
	struct MemoryBlock *tmp = m->head;		/* Bloque libre donde se guarda el pcb */
	struct MemoryBlock *tmp_ant = NULL;		/* Bloque anterior a tmp, para conectar la lista */
	enum AlgorithmMem alg = s->alg_memory;
	int blocks_needed = (p->mem.required_kb + BLOCK_SIZE - 1) / BLOCK_SIZE;

	if (blocks_needed <= 0 || blocks_needed > TOTAL_BLOCKS)
		return false;

	/*
	 * Cuando no queda ningún hueco libre, update_max_mem deja max en NULL.
	 * No se puede desreferenciar hasta que otro proceso libere memoria.
	 */
	if (m->max == NULL || blocks_needed > m->max->length)
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

	if (s->alg_sched == ROUND && sc->remaining_quantum <= 0)
		sc->remaining_quantum = s->quantum;
	
	s->cpu_busy = true;
}

void dispatch_save_ctx(struct Simulator *s)
{
	struct Pcb *p = s->running;
	struct ContextList *c = &s->context_list;
	struct ContextNode *tmp;
	
	/* No hay contexto para guardar */
	if (p == NULL)
		return;

	for (tmp = c->head; tmp != NULL; tmp = tmp->next) {
		if (*tmp->pid == p->pid) {
			tmp->ctx = p->cpu_ctx;
			p->cpu_ctx.new = false;
			return;
		}
	}

	struct ContextNode *cn = malloc(sizeof(struct ContextNode));

	if (!cn) {
		fprintf(stderr, "OOM en save_ctx.\n");
		exit(1);
	}

	cn->ctx = p->cpu_ctx;
	cn->pid = &p->pid;
	cn->next = c->head;
	c->head = cn;
	c->count++;
	p->cpu_ctx.new = false;
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
			if (p->mem.required_kb <= 0 ||
			    p->mem.required_kb > TOTAL_BLOCKS * BLOCK_SIZE) {
				p->state = ERROR_STATE;
				p->err.has_error = true;
				snprintf(p->err.error_code, sizeof(p->err.error_code), "ERR_MEM");
				snprintf(p->err.error_desc, sizeof(p->err.error_desc),
					"Memoria invalida: %d KB", p->mem.required_kb);
				enqueue(&s->finished_q, p);
				dequeue_pcb(jq, p);
				continue;
			}

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
		case P_SJF:
			p = alg_sjf(s);
			s->next_pcb = p;
			break;

		case ROUND:
			p = alg_fcfs(s);
			s->next_pcb = p;
			break;

		case NP_PRIOR:
		case P_PRIOR:
			p = alg_priority(s);
			s->next_pcb = p;
			break;
		
		default:
			s->next_pcb = NULL;
			break;
	}
}

struct Pcb *alg_fcfs(struct Simulator *s)
{
	return dequeue_head(&(s->ready_q));
}

struct Pcb *alg_sjf(struct Simulator *s)	// Shortest Job First
{
	struct Queue *rq = &s->ready_q;
	struct Node *tmp = rq->head;
	struct Pcb *p = tmp->pcb;	/* Pcb con el menor tiempo restante (remaining_time) */

	tmp = tmp->next;
	while (tmp != NULL) {
		double tmp_time = tmp->pcb->sched.remaining_time;
		double min_time = p->sched.remaining_time;

		if (tmp_time < min_time)
			p = tmp->pcb;

		tmp = tmp->next;
	}

	dequeue_pcb(&s->ready_q, p);

	return p;
}

struct Pcb *alg_priority(struct Simulator *s)
{
	struct Queue *rq = &s->ready_q;
	struct Node *tmp = rq->head;
	struct Pcb *p = tmp->pcb;

	tmp = tmp->next;
	while (tmp != NULL) {
		if (tmp->pcb->sched.priority < p->sched.priority)
			p = tmp->pcb;
		tmp = tmp->next;
	}

	dequeue_pcb(rq, p);
	return p;
}

/* Gestion de PCB*/
struct Pcb create_pcb(struct Simulator *s, char *name, int mem_kb,
		      double burst, double arrival, int priority)
{
	struct Pcb p = {0};
	
	snprintf(p.name, sizeof(p.name), "%s", name);
	
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
	p.io.start_time = (float)(burst * (0.1 + (double)(rand() % 80) / 100.0));/* io entre el 10-90% del burst */
	p.io.duration	= -1.0f;
	p.io.device 	= IO_NONE;
	
	if (p.io.has_io) {
		p.io.duration = 1.0f + (float)(rand() % 10);  	/* entre 1 y 10 u.t. */
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

void create_random_processes(struct Simulator *s)
{
	for (int i = 0; i < RANDOM_PROCESS_COUNT; i++) {
		char name[16];
		int memory = (1 + rand() % 16) * 64;
		double burst = 1.0 + rand() % 18;
		double arrival = rand() % 13;
		int priority = rand() % 10;
		struct Pcb *p = malloc(sizeof(struct Pcb));

		if (!p) {
			fprintf(stderr, "OOM al crear proceso aleatorio.\n");
			return;
		}

		snprintf(name, sizeof(name), "P%d", s->next_pid);
		*p = create_pcb(s, name, memory, burst, arrival, priority);
		enqueue(&s->created_processes, p);
		log_add(p);
	}
}

/* Diagrama de Gantt */
void create_gantt_node(struct Simulator *s)
{
	struct Pcb *p = s->running;
	struct GanttList *g = &s->gantt;
	struct GanttNode *new = malloc(sizeof(struct GanttNode));

	if (new == NULL) {
		fprintf(stderr, "OOM en create_gantt_node.\n");
		return;
	}

	new->start = s->current_time - TICK;
	new->limit = s->current_time;
	new->owner = p->pid;
	snprintf(new->name, sizeof(new->name), "%s", p->name);
	new->next = NULL;

	g->cont++;

	if (g->head == NULL) {
		g->head = new;
		return;
	}

	new->next = g->head;
	g->head = new;
}

void update_gantt(struct Simulator *s)
{
	struct Pcb *p = s->running;
	struct GanttNode *h = s->gantt.head;

	/* CPU idle */
	if (!s->cpu_busy)
		return;

	/* Primer proceso */
	if (h == NULL) {
		create_gantt_node(s);
		return;
	}

	if (p->pid == h->owner)	/* Actualizar */
		h->limit = s->current_time;
	else				/* Nuevo */
		create_gantt_node(s);
}

/* Main loop */
void sleep_microseconds(unsigned int microseconds)
{
	static HANDLE timer = NULL;
	LARGE_INTEGER due_time;

	if (timer == NULL)
		timer = CreateWaitableTimer(NULL, TRUE, NULL);

	if (timer != NULL) {
		due_time.QuadPart = -((LONGLONG)microseconds * 10);
		if (SetWaitableTimer(timer, &due_time, 0, NULL, NULL, FALSE)) {
			WaitForSingleObject(timer, INFINITE);
			return;
		}
	}

	Sleep((microseconds + 999) / 1000);
}

bool stdin_has_data(void)
{
	HANDLE input = GetStdHandle(STD_INPUT_HANDLE);
	DWORD available = 0;

	if (input == NULL || input == INVALID_HANDLE_VALUE)
		return false;

	/*
	 * Python inicia este programa con stdin conectado a una tubería.
	 * PeekNamedPipe permite comprobar si hay una orden sin bloquear
	 * el ciclo de simulación.
	 */
	if (GetFileType(input) == FILE_TYPE_PIPE)
		return PeekNamedPipe(input, NULL, 0, NULL, &available, NULL)
			&& available > 0;

	/* También permite ejecutar el simulador manualmente en una consola. */
	return WaitForSingleObject(input, 0) == WAIT_OBJECT_0;
}

void process_stdin(struct Simulator *s, char *line)
{
	if (strncmp(line, "CONFIG", 6) == 0) {
		int alg_sched, alg_mem;
		double quantum;

		sscanf(line, "CONFIG %d %d %lf", &alg_sched, &alg_mem, &quantum);

		s->alg_sched 	= (enum AlgorithmSched)alg_sched;
		s->alg_memory 	= (enum AlgorithmMem)alg_mem;
		s->quantum 	= quantum;

		log_config(s);
	} else if (strncmp(line, "ADD", 3) == 0) {
		char name[16];
		double burst, arrival;
		int mem_kb, priority;

		sscanf(line, "ADD %15s %d %lf %lf %d",
			name, &mem_kb, &burst, &arrival, &priority);

		struct Pcb *p = malloc(sizeof(struct Pcb));

		if (!p) {
			fprintf(stderr, "OOM al crear proceso.\n");
			return;
		}

		*p = create_pcb(s, name, mem_kb, burst, arrival, priority);

		enqueue(&s->created_processes, p);

		log_add(p);
		send_data(s);
	} else if (strncmp(line, "RANDOM", 6) == 0) {
		create_random_processes(s);
		send_data(s);
	} else if (strncmp(line, "RUN", 3) == 0) {
		s->state = SIM_RUN;
		log_run();
	} else if (strncmp(line, "PAUSE", 5) == 0) {
		s->state = SIM_PAUSE;
		log_pause();
	} else if (strncmp(line, "STOP", 4) == 0) {
		s->state = SIM_STOP;
		log_stop();
	}
}

bool should_preempt(struct Simulator *s)
{
	struct Node *tmp;

	if (s->running == NULL || s->ready_q.head == NULL)
		return false;

	for (tmp = s->ready_q.head; tmp != NULL; tmp = tmp->next) {
		if (s->alg_sched == P_SJF &&
		    tmp->pcb->sched.remaining_time < s->running->sched.remaining_time)
			return true;
		if (s->alg_sched == P_PRIOR &&
		    tmp->pcb->sched.priority < s->running->sched.priority)
			return true;
	}

	return false;
}

void tick_running_process(struct Simulator *s)
{
	struct Pcb *p = s->running;

	if (p == NULL)		/* wason */
		return;

	p->sched.remaining_time -= TICK;
	p->cpu_ctx.program_counter++;	/* al fin el program counter (mostrar en hexa) */

	if (s->alg_sched == ROUND)
		p->sched.remaining_quantum -= TICK;

	if (p->sched.remaining_time <= TIME_EPSILON) {
		terminate_running_process(s);
		return;
	}

	if (s->alg_sched == ROUND && p->sched.remaining_quantum <= 0) {
		p->sched.remaining_quantum = s->quantum;
		p->state = READY;
		enqueue(&s->ready_q, p);
		s->running = NULL;
		s->cpu_busy = false;
	}
}

void main_loop(struct Simulator *s)
{
	if (s->created_processes.cont > 0)			/* Entran procesos a job_q */
		process_arrival(s);				/* segun arrival_time */

	if (s->job_q.cont > 0)					/* Si existen procesos no listos */
		job_scheduler(s);				/* se agregan a ready_q */

	if (should_preempt(s)) {
		s->running->state = READY;
		enqueue(&s->ready_q, s->running);
		scheduler(s);
		dispatch(s);
	}

	if (s->running == NULL && s->ready_q.cont > 0) {	/* Cpu libre y procesos listos */
		scheduler(s);
		dispatch(s);
	}

	update_gantt(s);
	tick_running_process(s);

	if (s->created_processes.cont == 0 &&
	    s->job_q.cont == 0		   &&
	    s->ready_q.cont == 0	   &&
	    s->running == NULL)					/* Se terminan todos los procesos */
		s->state = SIM_STOP;				/* y la CPU deja de trabajar */

	/* Imprimir - deprecated */
	// print_main_loop(s);
	send_data(s);
}

int main(void)
{
	struct Simulator simulator = simulator_init();
	struct Simulator *s = &simulator;
	char line[256];

	srand((unsigned int)time(NULL));

	setvbuf(stdin,  NULL, _IONBF, 0);	/* La tubería y fgets ven las mismas órdenes */
	setvbuf(stdout, NULL, _IOLBF, 0);	/* stdout sale linea por linea (como un printf creo) */

	while (s->state != SIM_STOP) {
		sleep_microseconds(TICK_US);

		if (stdin_has_data()) {
			if (fgets(line, sizeof(line), stdin) != NULL)
				process_stdin(s, line);
		}

		if (s->state == SIM_PAUSE)
			continue;

		s->current_time += TICK;
		main_loop(s);
	}

	if (s->running != NULL)
		free(s->running);
	q_free(&s->created_processes);
	q_free(&s->job_q);
	q_free(&s->ready_q);
	q_free(&s->io_q);
	q_free(&s->finished_q);

	return 0;
}

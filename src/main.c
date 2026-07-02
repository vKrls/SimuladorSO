#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define TICK 0.1
#define TICK_US 100000
#define TIME_EPSILON 1e-9
#define SNAPSHOT_INTERVAL_MS 100

#define TOTAL_MEMORY_KB (1024 * 1024)
#define BLOCK_SIZE_KB 4
#define TOTAL_BLOCKS (TOTAL_MEMORY_KB / BLOCK_SIZE_KB)
#define OS_RESERVED_KB (128 * 1024)
#define USER_MEMORY_KB (TOTAL_MEMORY_KB - OS_RESERVED_KB)

#define RESERVED_PID_COUNT 100
#define OS_PROCESS_COUNT 5
#define RANDOM_PROCESS_COUNT 5
#define IO_DEVICE_COUNT 5
#define MAX_INTERRUPT_HISTORY 32
#define ERR_CODE_MAX 24
#define ERR_DESC_MAX 96

enum SimulatorState {
	SIM_RUN = 0,
	SIM_PAUSE = 1,
	SIM_STOP = 2,
};

enum AlgorithmSched {
	FCFS = 0,
	NP_SJF = 1,
	P_SJF = 2,
	ROUND = 3,
	NP_PRIOR = 4,
	P_PRIOR = 5,
};

enum AlgorithmMem {
	FIRST = 0,
	BEST = 1,
	WORST = 2,
};

enum ProcessState {
	NEW = 0,
	READY = 1,
	RUNNING = 2,
	BLOCKED = 3,
	TERMINATED = 4,
};

enum IoDevice {
	IO_NONE = -1,
	IO_KEYBOARD = 0,
	IO_MOUSE = 1,
	IO_DISK = 2,
	IO_PRINTER = 3,
	IO_NETWORK = 4,
};

enum IntType {
	INT_HW_IO = 0,
	INT_HW_TIMER = 1,
	INT_SW_SYSCALL = 2,
	INT_EXC_DIV_ZERO = 3,
	INT_EXC_MEM = 4,
	INT_TYPE_COUNT = 5,
};

enum GanttType {
	GANTT_PROCESS = 0,
	GANTT_IDLE = 1,
	GANTT_CONTEXT_SWITCH = 2,
};

struct Pcb;
struct MemoryBlock;

struct CpuContext {
	int program_counter;
	int stack_pointer;
};

struct SchedulerData {
	double arrival_time;		/* Tiempo en que ingresa al sistema */
	double burst_time;		/* Constante */
	double remaining_time;		/* Burst restante */
	double start_time;		/* Primera vez que entra a running */
	double finish_time;		/* Se acaba el burst */
	double turnaround_time;		/*  */
	double response_time;
	double ready_time;
	double blocked_time;
	double nonresident_time;
	double cpu_time;
	int priority;
	double remaining_quantum;
	int context_switches;
};

struct MemoryData {
	int required_kb;
	int assigned_blocks;
	int waste_kb;
	int start;
	int limit;
	struct MemoryBlock *block;	/* Direccion de memoria */
};

struct IoData {
	bool has_io;
	bool started;
	bool completed;
	double start_time;
	double duration;
	double remaining_time;
	enum IoDevice device;
};

struct InterruptEvent {
	enum IntType type;
	enum IoDevice device;
	double time;
	bool fatal;
};

struct InterruptData {
	int periodic_target;
	int periodic_done;
	double next_cpu_time;
	int total;
	int by_type[INT_TYPE_COUNT];
	int history_count;
	struct InterruptEvent history[MAX_INTERRUPT_HISTORY];
};

struct ErrorData {
	bool planned;
	bool has_error;
	bool fatal;
	enum IntType planned_type;
	double trigger_cpu_time;
	double occurred_at;
	char error_code[ERR_CODE_MAX];
	char error_desc[ERR_DESC_MAX];
};

struct Pcb {
	char name[16];
	int pid;
	enum ProcessState state;
	bool is_system;
	bool resident;
	int swap_count;
	double last_swap_out;
	double last_swap_in;
	struct CpuContext cpu_ctx;
	struct MemoryData mem;
	struct SchedulerData sched;
	struct IoData io;
	struct ErrorData err;
	struct InterruptData interrupt;
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
	struct Pcb *owner;
	struct MemoryBlock *next;
};

struct MemoryBlockList {
	int cont;
	int free;
	struct MemoryBlock *head;
	struct MemoryBlock *tail;
	struct MemoryBlock *max;
};

struct GanttNode {
	double start;
	double limit;
	enum GanttType type;
	int owner;
	char name[16];
	struct GanttNode *next;
};

struct GanttList {
	int cont;
	struct GanttNode *head;
	struct GanttNode *tail;
};

struct Simulator {
	enum SimulatorState state;
	double current_time;
	int sim_speed;
	int next_pid;

	enum AlgorithmSched alg_sched;
	enum AlgorithmMem alg_memory;
	double quantum;
	double switch_cost;
	double switch_remaining;

	struct Queue system_q;
	struct Queue created_processes;
	struct Queue job_q;
	struct Queue ready_q;
	struct Queue device_q[IO_DEVICE_COUNT];
	struct Queue nonresident_q;
	struct Queue finished_q;

	struct Pcb *running;
	struct Pcb *next_pcb;
	struct CpuContext cpu_ctx;
	bool cpu_busy;

	struct MemoryBlockList memory_list;
	struct GanttList gantt;

	int user_process_count;
	int completed_count;
	int error_count;
	int interrupt_count;
	int swap_out_count;
	int swap_in_count;
	int context_switch_count;
	double cpu_process_time;
	double idle_time;
	double context_switch_time;

	uint64_t snapshot_sequence;
	int64_t last_snapshot_ms;
};

/* Nombres y logs */
const char *process_state_name(enum ProcessState state);
const char *scheduler_algorithm_name(enum AlgorithmSched algorithm);
const char *memory_algorithm_name(enum AlgorithmMem algorithm);
const char *io_device_name(enum IoDevice device);
const char *interrupt_type_name(enum IntType type);
const char *gantt_type_name(enum GanttType type);
void log_event(struct Simulator *s, const char *category, const char *format, ...);
void set_process_state(struct Simulator *s, struct Pcb *p,
		       enum ProcessState state, const char *reason);

/* Colas */
struct Queue init_queue(void);
bool q_empty(const struct Queue *q);
void enqueue(struct Queue *q, struct Pcb *p);
struct Pcb *dequeue_head(struct Queue *q);
void dequeue_pcb(struct Queue *q, struct Pcb *p);
void q_free(struct Queue *q);
void accumulate_queue_time(struct Queue *q, double delta, int kind);

/* Memoria */
struct MemoryBlockList mem_init(void);
void update_max_mem(struct MemoryBlockList *m);
bool kmalloc(struct Simulator *s, struct Pcb *p);
void kfree(struct MemoryBlockList *m, struct Pcb *p);
void kmerge(struct MemoryBlockList *m);
bool memory_can_fit(struct Simulator *s, struct Pcb *p);
void memory_free_all(struct MemoryBlockList *m);

/* Procesos */
struct Pcb create_user_pcb(struct Simulator *s, const char *name, int mem_kb,
			   double burst, double arrival, int priority);
void create_random_processes(struct Simulator *s);
void create_system_processes(struct Simulator *s);
void finish_process(struct Simulator *s, struct Pcb *p, bool failed);
void terminate_running_process(struct Simulator *s);
void fail_running_process(struct Simulator *s, enum IntType type,
			  const char *code, const char *description);

/* Interrupciones, I/O y swap */
void record_interrupt(struct Simulator *s, struct Pcb *p, enum IntType type,
		      enum IoDevice device, bool fatal);
void running_to_blocked(struct Simulator *s);
void blocked_to_ready(struct Simulator *s, struct Pcb *p, enum IoDevice device);
void tick_device_queues(struct Simulator *s, double delta);
void mid_term_scheduler(struct Simulator *s);

/* Planificación y CPU */
void process_arrival(struct Simulator *s);
void job_scheduler(struct Simulator *s);
void scheduler(struct Simulator *s);
struct Pcb *alg_fcfs(struct Simulator *s);
struct Pcb *alg_sjf(struct Simulator *s);
struct Pcb *alg_priority(struct Simulator *s);
bool should_preempt(struct Simulator *s);
void dispatch_save_ctx(struct Simulator *s);
void dispatch_restore_ctx(struct Simulator *s, struct Pcb *p);
void dispatch(struct Simulator *s);
void begin_context_switch(struct Simulator *s);
void tick_running_process(struct Simulator *s, double delta);

/* Gantt y ciclo */
struct GanttList gantt_init(void);
void update_gantt_interval(struct Simulator *s, enum GanttType type,
			   struct Pcb *p, double delta);
void gantt_free(struct GanttList *g);
void tick_background(struct Simulator *s, double delta);
bool simulation_finished(struct Simulator *s);
void main_loop(struct Simulator *s);

/* Protocolo */
void send_json_string(const char *text);
void send_data(struct Simulator *s, bool force);
void process_stdin(struct Simulator *s, char *line);
bool stdin_has_data(void);

static int64_t monotonic_ms(void)
{
	struct timespec now;

	clock_gettime(CLOCK_MONOTONIC, &now);
	return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

const char *process_state_name(enum ProcessState state)
{
	switch (state) {
	case NEW: return "NEW";
	case READY: return "READY";
	case RUNNING: return "RUNNING";
	case BLOCKED: return "BLOCKED";
	case TERMINATED: return "TERMINATED";
	default: return "UNKNOWN";
	}
}

const char *scheduler_algorithm_name(enum AlgorithmSched algorithm)
{
	switch (algorithm) {
	case FCFS: return "FCFS";
	case NP_SJF: return "SJF no expropiativo";
	case P_SJF: return "SJF expropiativo";
	case ROUND: return "Round Robin";
	case NP_PRIOR: return "Prioridad no expropiativa";
	case P_PRIOR: return "Prioridad expropiativa";
	default: return "Desconocido";
	}
}

const char *memory_algorithm_name(enum AlgorithmMem algorithm)
{
	switch (algorithm) {
	case FIRST: return "First Fit";
	case BEST: return "Best Fit";
	case WORST: return "Worst Fit";
	default: return "Desconocido";
	}
}

const char *io_device_name(enum IoDevice device)
{
	switch (device) {
	case IO_KEYBOARD: return "KEYBOARD";
	case IO_MOUSE: return "MOUSE";
	case IO_DISK: return "DISK";
	case IO_PRINTER: return "PRINTER";
	case IO_NETWORK: return "NETWORK";
	default: return "NONE";
	}
}

const char *interrupt_type_name(enum IntType type)
{
	switch (type) {
	case INT_HW_IO: return "HW_IO";
	case INT_HW_TIMER: return "HW_TIMER";
	case INT_SW_SYSCALL: return "SW_SYSCALL";
	case INT_EXC_DIV_ZERO: return "EXC_DIV_ZERO";
	case INT_EXC_MEM: return "EXC_MEMORY";
	default: return "UNKNOWN";
	}
}

const char *gantt_type_name(enum GanttType type)
{
	switch (type) {
	case GANTT_PROCESS: return "PROCESS";
	case GANTT_IDLE: return "IDLE";
	case GANTT_CONTEXT_SWITCH: return "CONTEXT_SWITCH";
	default: return "UNKNOWN";
	}
}

void log_event(struct Simulator *s, const char *category, const char *format, ...)
{
	va_list args;
	double current_time = s == NULL ? 0.0 : s->current_time;

	printf("LOG [t=%.3f] [%s] ", current_time, category);
	va_start(args, format);
	vprintf(format, args);
	va_end(args);
	putchar('\n');
	fflush(stdout);
}

void set_process_state(struct Simulator *s, struct Pcb *p,
		       enum ProcessState state, const char *reason)
{
	enum ProcessState previous;

	if (p == NULL)
		return;
	previous = p->state;
	p->state = state;
	if (previous != state) {
		log_event(s, "STATE", "%s(%d): %s -> %s; causa=%s.",
			  p->name, p->pid, process_state_name(previous),
			  process_state_name(state), reason);
	}
}

struct Queue init_queue(void)
{
	struct Queue q = {0};
	return q;
}

bool q_empty(const struct Queue *q)
{
	return q->head == NULL;
}

void enqueue(struct Queue *q, struct Pcb *p)
{
	struct Node *node = malloc(sizeof(*node));

	if (node == NULL) {
		fprintf(stderr, "OOM al encolar un proceso.\n");
		exit(EXIT_FAILURE);
	}
	node->pcb = p;
	node->next = NULL;
	if (q->tail == NULL)
		q->head = node;
	else
		q->tail->next = node;
	q->tail = node;
	q->cont++;
}

struct Pcb *dequeue_head(struct Queue *q)
{
	struct Node *node;
	struct Pcb *p;

	if (q_empty(q))
		return NULL;
	node = q->head;
	p = node->pcb;
	q->head = node->next;
	if (q->head == NULL)
		q->tail = NULL;
	q->cont--;
	free(node);
	return p;
}

void dequeue_pcb(struct Queue *q, struct Pcb *p)
{
	struct Node *node = q->head;
	struct Node *previous = NULL;

	while (node != NULL) {
		if (node->pcb == p) {
			if (previous == NULL)
				q->head = node->next;
			else
				previous->next = node->next;
			if (q->tail == node)
				q->tail = previous;
			q->cont--;
			free(node);
			return;
		}
		previous = node;
		node = node->next;
	}
}

void q_free(struct Queue *q)
{
	while (!q_empty(q))
		free(dequeue_head(q));
}

void accumulate_queue_time(struct Queue *q, double delta, int kind)
{
	struct Node *node;

	for (node = q->head; node != NULL; node = node->next) {
		if (kind == 0)
			node->pcb->sched.ready_time += delta;
		else if (kind == 1)
			node->pcb->sched.blocked_time += delta;
		else
			node->pcb->sched.nonresident_time += delta;
	}
}

struct MemoryBlockList mem_init(void)
{
	struct MemoryBlockList m = {0};
	struct MemoryBlock *block = malloc(sizeof(*block));

	if (block == NULL) {
		fprintf(stderr, "OOM al inicializar la memoria.\n");
		exit(EXIT_FAILURE);
	}
	block->start = 0;
	block->limit = TOTAL_BLOCKS;
	block->length = TOTAL_BLOCKS;
	block->owner = NULL;
	block->next = NULL;
	m.cont = 1;
	m.free = TOTAL_BLOCKS;
	m.head = block;
	m.tail = block;
	m.max = block;
	return m;
}

void update_max_mem(struct MemoryBlockList *m)
{
	struct MemoryBlock *block;

	m->max = NULL;
	for (block = m->head; block != NULL; block = block->next) {
		if (block->owner == NULL &&
		    (m->max == NULL || block->length > m->max->length))
			m->max = block;
	}
}

static bool allocate_block(struct MemoryBlockList *m, struct MemoryBlock *free_block,
			   struct MemoryBlock *previous, struct Pcb *p,
			   int blocks_needed)
{
	struct MemoryBlock *allocated = malloc(sizeof(*allocated));

	if (allocated == NULL)
		return false;
	allocated->start = free_block->start;
	allocated->limit = free_block->start + blocks_needed;
	allocated->length = blocks_needed;
	allocated->owner = p;

	if (blocks_needed == free_block->length) {
		allocated->next = free_block->next;
		if (previous == NULL)
			m->head = allocated;
		else
			previous->next = allocated;
		if (m->tail == free_block)
			m->tail = allocated;
		free(free_block);
	} else {
		allocated->next = free_block;
		free_block->start = allocated->limit;
		free_block->length = free_block->limit - free_block->start;
		if (previous == NULL)
			m->head = allocated;
		else
			previous->next = allocated;
		m->cont++;
	}

	p->mem.block = allocated;
	p->mem.start = allocated->start;
	p->mem.limit = allocated->limit;
	p->mem.assigned_blocks = blocks_needed;
	p->mem.waste_kb = blocks_needed * BLOCK_SIZE_KB - p->mem.required_kb;
	p->resident = true;
	m->free -= blocks_needed;
	update_max_mem(m);
	return true;
}

bool memory_can_fit(struct Simulator *s, struct Pcb *p)
{
	int needed = (p->mem.required_kb + BLOCK_SIZE_KB - 1) / BLOCK_SIZE_KB;
	return needed > 0 && s->memory_list.max != NULL &&
	       needed <= s->memory_list.max->length;
}

bool kmalloc(struct Simulator *s, struct Pcb *p)
{
	struct MemoryBlockList *m = &s->memory_list;
	struct MemoryBlock *block = m->head;
	struct MemoryBlock *previous = NULL;
	struct MemoryBlock *selected = NULL;
	struct MemoryBlock *selected_previous = NULL;
	int needed = (p->mem.required_kb + BLOCK_SIZE_KB - 1) / BLOCK_SIZE_KB;

	if (needed <= 0 || needed > TOTAL_BLOCKS || !memory_can_fit(s, p))
		return false;

	while (block != NULL) {
		if (block->owner == NULL && block->length >= needed) {
			if (s->alg_memory == FIRST) {
				selected = block;
				selected_previous = previous;
				break;
			}
			if (selected == NULL ||
			    (s->alg_memory == BEST && block->length < selected->length) ||
			    (s->alg_memory == WORST && block->length > selected->length)) {
				selected = block;
				selected_previous = previous;
			}
		}
		previous = block;
		block = block->next;
	}
	return selected != NULL &&
	       allocate_block(m, selected, selected_previous, p, needed);
}

void kmerge(struct MemoryBlockList *m)
{
	struct MemoryBlock *block = m->head;

	while (block != NULL && block->next != NULL) {
		if (block->owner == NULL && block->next->owner == NULL) {
			struct MemoryBlock *discard = block->next;
			block->limit = discard->limit;
			block->length += discard->length;
			block->next = discard->next;
			if (m->tail == discard)
				m->tail = block;
			free(discard);
			m->cont--;
		} else {
			block = block->next;
		}
	}
	update_max_mem(m);
}

void kfree(struct MemoryBlockList *m, struct Pcb *p)
{
	struct MemoryBlock *block = p->mem.block;

	if (block == NULL || block->owner != p)
		return;
	block->owner = NULL;
	m->free += block->length;
	p->mem.block = NULL;
	p->mem.start = -1;
	p->mem.limit = -1;
	p->mem.assigned_blocks = 0;
	p->mem.waste_kb = 0;
	p->resident = false;
	kmerge(m);
}

void memory_free_all(struct MemoryBlockList *m)
{
	struct MemoryBlock *block = m->head;
	while (block != NULL) {
		struct MemoryBlock *next = block->next;
		free(block);
		block = next;
	}
}

static struct Pcb pcb_defaults(void)
{
	struct Pcb p;

	memset(&p, 0, sizeof(p));
	p.mem.start = -1;
	p.mem.limit = -1;
	p.sched.start_time = -1.0;
	p.sched.finish_time = -1.0;
	p.io.device = IO_NONE;
	p.io.duration = -1.0;
	p.io.remaining_time = -1.0;
	p.err.occurred_at = -1.0;
	p.last_swap_out = -1.0;
	p.last_swap_in = -1.0;
	return p;
}

struct Pcb create_user_pcb(struct Simulator *s, const char *name, int mem_kb,
			   double burst, double arrival, int priority)
{
	struct Pcb p = pcb_defaults();
	double memory_factor;
	double burst_factor;

	snprintf(p.name, sizeof(p.name), "%s", name);
	p.pid = s->next_pid++;
	p.state = NEW;
	p.mem.required_kb = mem_kb;
	p.sched.arrival_time = arrival;
	p.sched.burst_time = burst;
	p.sched.remaining_time = burst;
	p.sched.priority = priority;
	p.sched.remaining_quantum = s->quantum;
	p.cpu_ctx.stack_pointer = 0x1000 + p.pid * 16;

	p.io.has_io = rand() % 100 < 65;
	p.io.start_time = burst * (0.15 + (rand() % 66) / 100.0);
	if (p.io.has_io) {
		p.io.duration = 0.5 + (rand() % 76) / 10.0;
		p.io.remaining_time = p.io.duration;
		p.io.device = (enum IoDevice)(rand() % IO_DEVICE_COUNT);
	}

	memory_factor = (double)mem_kb / (192.0 * 1024.0);
	burst_factor = burst / 30.0;
	p.interrupt.periodic_target = 2 + (int)((memory_factor + burst_factor) * 3.0);
	if (p.interrupt.periodic_target > 12)
		p.interrupt.periodic_target = 12;
	p.interrupt.next_cpu_time =
		burst / (p.interrupt.periodic_target + 1.0);

	p.err.planned = rand() % 100 < 5;
	if (p.err.planned) {
		p.err.planned_type =
			rand() % 2 == 0 ? INT_EXC_DIV_ZERO : INT_EXC_MEM;
		p.err.trigger_cpu_time =
			burst * (0.20 + (rand() % 61) / 100.0);
	}
	s->user_process_count++;
	return p;
}

void create_random_processes(struct Simulator *s)
{
	int i;

	for (i = 0; i < RANDOM_PROCESS_COUNT; i++) {
		struct Pcb *p = malloc(sizeof(*p));
		char name[16];
		int memory = (24 + rand() % 169) * 1024;
		double burst = 4.0 + rand() % 27;
		double arrival = rand() % 13;
		int priority = rand() % 10;

		if (p == NULL) {
			fprintf(stderr, "OOM al crear un proceso aleatorio.\n");
			return;
		}
		snprintf(name, sizeof(name), "P%d", s->next_pid);
		*p = create_user_pcb(s, name, memory, burst, arrival, priority);
		enqueue(&s->created_processes, p);
		log_event(s, "PROCESS", "%s(%d) creado: memoria=%d MB, burst=%.1f.",
			  p->name, p->pid, p->mem.required_kb / 1024,
			  p->sched.burst_time);
	}
}

void create_system_processes(struct Simulator *s)
{
	static const char *names[OS_PROCESS_COUNT] = {
		"Kernel", "MemoryMgr", "Scheduler", "IOManager", "Swapper"
	};
	int blocks[OS_PROCESS_COUNT] = {
		(48 * 1024) / BLOCK_SIZE_KB,
		(20 * 1024) / BLOCK_SIZE_KB,
		(16 * 1024) / BLOCK_SIZE_KB,
		(16 * 1024) / BLOCK_SIZE_KB,
		(8 * 1024) / BLOCK_SIZE_KB,
	};
	int assigned = (108 * 1024) / BLOCK_SIZE_KB;
	int i;

	while (assigned < OS_RESERVED_KB / BLOCK_SIZE_KB) {
		blocks[rand() % OS_PROCESS_COUNT]++;
		assigned++;
	}

	for (i = 0; i < OS_PROCESS_COUNT; i++) {
		struct Pcb *p = malloc(sizeof(*p));
		if (p == NULL) {
			fprintf(stderr, "OOM al crear procesos del SO.\n");
			exit(EXIT_FAILURE);
		}
		*p = pcb_defaults();
		snprintf(p->name, sizeof(p->name), "%s", names[i]);
		p->pid = i;
		p->state = BLOCKED;
		p->is_system = true;
		p->mem.required_kb = blocks[i] * BLOCK_SIZE_KB;
		p->sched.priority = 0;
		p->resident = false;
		if (!kmalloc(s, p)) {
			fprintf(stderr, "No se pudo reservar memoria para %s.\n", p->name);
			free(p);
			exit(EXIT_FAILURE);
		}
		enqueue(&s->system_q, p);
	}
}

void record_interrupt(struct Simulator *s, struct Pcb *p, enum IntType type,
		      enum IoDevice device, bool fatal)
{
	struct InterruptData *data = &p->interrupt;
	struct InterruptEvent *event;

	if (data->history_count == MAX_INTERRUPT_HISTORY) {
		memmove(&data->history[0], &data->history[1],
			sizeof(data->history[0]) * (MAX_INTERRUPT_HISTORY - 1));
		data->history_count--;
	}
	event = &data->history[data->history_count++];
	event->type = type;
	event->device = device;
	event->time = s->current_time;
	event->fatal = fatal;
	data->total++;
	if (type >= 0 && type < INT_TYPE_COUNT)
		data->by_type[type]++;
	s->interrupt_count++;
	log_event(s, "INTERRUPT", "%s(%d): %s%s%s.",
		  p->name, p->pid, interrupt_type_name(type),
		  device == IO_NONE ? "" : " dispositivo=",
		  device == IO_NONE ? "" : io_device_name(device));
}

void finish_process(struct Simulator *s, struct Pcb *p, bool failed)
{
	p->sched.remaining_time = failed ? p->sched.remaining_time : 0.0;
	p->sched.finish_time = s->current_time;
	p->sched.turnaround_time =
		p->sched.finish_time - p->sched.arrival_time;
	set_process_state(s, p, TERMINATED,
			  failed ? "terminado por excepción fatal"
				 : "ráfaga de CPU completada");
	kfree(&s->memory_list, p);
	enqueue(&s->finished_q, p);
	s->completed_count++;
	if (failed)
		s->error_count++;
}

void terminate_running_process(struct Simulator *s)
{
	struct Pcb *p = s->running;
	if (p == NULL)
		return;
	dispatch_save_ctx(s);
	finish_process(s, p, false);
	log_event(s, "CPU", "%s(%d) terminó.", p->name, p->pid);
	s->running = NULL;
	s->cpu_busy = false;
}

void fail_running_process(struct Simulator *s, enum IntType type,
			  const char *code, const char *description)
{
	struct Pcb *p = s->running;
	if (p == NULL)
		return;
	record_interrupt(s, p, type, IO_NONE, true);
	p->err.has_error = true;
	p->err.fatal = true;
	p->err.occurred_at = s->current_time;
	snprintf(p->err.error_code, sizeof(p->err.error_code), "%s", code);
	snprintf(p->err.error_desc, sizeof(p->err.error_desc), "%s", description);
	dispatch_save_ctx(s);
	finish_process(s, p, true);
	log_event(s, "ERROR", "%s(%d): %s - %s.", p->name, p->pid,
		  p->err.error_code, p->err.error_desc);
	s->running = NULL;
	s->cpu_busy = false;
}

void process_arrival(struct Simulator *s)
{
	struct Node *node = s->created_processes.head;

	while (node != NULL) {
		struct Pcb *p = node->pcb;
		node = node->next;
		if (p->sched.arrival_time <= s->current_time + TIME_EPSILON) {
			dequeue_pcb(&s->created_processes, p);
			enqueue(&s->job_q, p);
			log_event(s, "QUEUE", "%s(%d): created_processes -> job_q.",
				  p->name, p->pid);
		}
	}
}

void job_scheduler(struct Simulator *s)
{
	struct Node *node = s->job_q.head;

	while (node != NULL) {
		struct Pcb *p = node->pcb;
		node = node->next;
		if (p->mem.required_kb <= 0 || p->mem.required_kb > USER_MEMORY_KB) {
			p->err.has_error = true;
			p->err.fatal = true;
			p->err.occurred_at = s->current_time;
			snprintf(p->err.error_code, sizeof(p->err.error_code), "ERR_MEM_SIZE");
			snprintf(p->err.error_desc, sizeof(p->err.error_desc),
				 "Memoria fuera del rango de usuario: %d KB",
				 p->mem.required_kb);
			dequeue_pcb(&s->job_q, p);
			finish_process(s, p, true);
			continue;
		}
		if (!memory_can_fit(s, p) || !kmalloc(s, p))
			continue;
		dequeue_pcb(&s->job_q, p);
		set_process_state(s, p, READY, "admitido en memoria");
		enqueue(&s->ready_q, p);
		log_event(s, "SCHEDULER", "%s(%d) admitido por largo plazo.",
			  p->name, p->pid);
	}
}

static struct Pcb *blocked_swap_candidate(struct Simulator *s,
					  enum IoDevice *device)
{
	struct Pcb *candidate = NULL;
	int i;

	for (i = 0; i < IO_DEVICE_COUNT; i++) {
		struct Node *node;
		for (node = s->device_q[i].head; node != NULL; node = node->next) {
			struct Pcb *p = node->pcb;
			if (p->state != BLOCKED || !p->resident)
				continue;
			if (candidate == NULL ||
			    p->io.remaining_time > candidate->io.remaining_time ||
			    (p->io.remaining_time == candidate->io.remaining_time &&
			     p->mem.required_kb > candidate->mem.required_kb)) {
				candidate = p;
				*device = (enum IoDevice)i;
			}
		}
	}
	return candidate;
}

static struct Pcb *waiting_for_memory(struct Simulator *s)
{
	struct Node *node;

	for (node = s->nonresident_q.head; node != NULL; node = node->next)
		if (node->pcb->state == READY && !node->pcb->resident)
			return node->pcb;
	for (node = s->job_q.head; node != NULL; node = node->next)
		if (node->pcb->sched.arrival_time <= s->current_time + TIME_EPSILON)
			return node->pcb;
	return NULL;
}

static bool swap_in_ready_processes(struct Simulator *s)
{
	struct Node *node = s->nonresident_q.head;
	bool changed = false;

	while (node != NULL) {
		struct Pcb *p = node->pcb;
		node = node->next;
		if (p->state != READY || p->resident || !memory_can_fit(s, p) ||
		    !kmalloc(s, p))
			continue;
		dequeue_pcb(&s->nonresident_q, p);
		p->last_swap_in = s->current_time;
		enqueue(&s->ready_q, p);
		s->swap_in_count++;
		changed = true;
		log_event(s, "SWAPPER", "%s(%d) volvió a memoria.", p->name, p->pid);
	}
	return changed;
}

void mid_term_scheduler(struct Simulator *s)
{
	struct Pcb *waiting;

	swap_in_ready_processes(s);
	waiting = waiting_for_memory(s);
	while (waiting != NULL && !memory_can_fit(s, waiting)) {
		enum IoDevice device = IO_NONE;
		struct Pcb *candidate = blocked_swap_candidate(s, &device);
		if (candidate == NULL)
			break;
		kfree(&s->memory_list, candidate);
		candidate->swap_count++;
		candidate->last_swap_out = s->current_time;
		s->swap_out_count++;
		log_event(s, "SWAPPER", "%s(%d) descargado; libera %d MB.",
			  candidate->name, candidate->pid,
			  candidate->mem.required_kb / 1024);
		swap_in_ready_processes(s);
		waiting = waiting_for_memory(s);
	}
}

void running_to_blocked(struct Simulator *s)
{
	struct Pcb *p = s->running;

	if (p == NULL || p->io.device < 0 || p->io.device >= IO_DEVICE_COUNT)
		return;
	record_interrupt(s, p, INT_SW_SYSCALL, p->io.device, false);
	dispatch_save_ctx(s);
	p->io.started = true;
	p->io.remaining_time = p->io.duration;
	set_process_state(s, p, BLOCKED, "solicitud de entrada/salida");
	enqueue(&s->device_q[p->io.device], p);
	s->running = NULL;
	s->cpu_busy = false;
}

void blocked_to_ready(struct Simulator *s, struct Pcb *p, enum IoDevice device)
{
	p->io.remaining_time = 0.0;
	p->io.completed = true;
	record_interrupt(s, p, INT_HW_IO, device, false);
	dequeue_pcb(&s->device_q[device], p);
	set_process_state(s, p, READY, "entrada/salida completada");
	enqueue(&s->ready_q, p);
}

void tick_device_queues(struct Simulator *s, double delta)
{
	int i;

	for (i = 0; i < IO_DEVICE_COUNT; i++) {
		struct Pcb *p;
		if (q_empty(&s->device_q[i]))
			continue;
		p = s->device_q[i].head->pcb;
		p->io.remaining_time -= delta;
		if (p->io.remaining_time <= TIME_EPSILON && !p->resident) {
			p->io.remaining_time = 0.0;
			p->io.completed = true;
			record_interrupt(s, p, INT_HW_IO, p->io.device, false);
			dequeue_pcb(&s->device_q[i], p);
			set_process_state(s, p, READY,
					  "I/O terminó fuera de memoria");
			enqueue(&s->nonresident_q, p);
		} else if (p->io.remaining_time <= TIME_EPSILON) {
			blocked_to_ready(s, p, (enum IoDevice)i);
		}
	}
}

struct Pcb *alg_fcfs(struct Simulator *s)
{
	return dequeue_head(&s->ready_q);
}

struct Pcb *alg_sjf(struct Simulator *s)
{
	struct Node *node = s->ready_q.head;
	struct Pcb *selected = node == NULL ? NULL : node->pcb;

	for (; node != NULL; node = node->next)
		if (node->pcb->sched.remaining_time < selected->sched.remaining_time)
			selected = node->pcb;
	if (selected != NULL)
		dequeue_pcb(&s->ready_q, selected);
	return selected;
}

struct Pcb *alg_priority(struct Simulator *s)
{
	struct Node *node = s->ready_q.head;
	struct Pcb *selected = node == NULL ? NULL : node->pcb;

	for (; node != NULL; node = node->next)
		if (node->pcb->sched.priority < selected->sched.priority)
			selected = node->pcb;
	if (selected != NULL)
		dequeue_pcb(&s->ready_q, selected);
	return selected;
}

void scheduler(struct Simulator *s)
{
	switch (s->alg_sched) {
	case FCFS:
	case ROUND:
		s->next_pcb = alg_fcfs(s);
		break;
	case NP_SJF:
	case P_SJF:
		s->next_pcb = alg_sjf(s);
		break;
	case NP_PRIOR:
	case P_PRIOR:
		s->next_pcb = alg_priority(s);
		break;
	default:
		s->next_pcb = NULL;
		break;
	}
	if (s->next_pcb != NULL)
		log_event(s, "SCHEDULER", "Seleccionado %s(%d).",
			  s->next_pcb->name, s->next_pcb->pid);
}

bool should_preempt(struct Simulator *s)
{
	struct Node *node;

	if (s->running == NULL)
		return false;
	for (node = s->ready_q.head; node != NULL; node = node->next) {
		if (s->alg_sched == P_SJF &&
		    node->pcb->sched.remaining_time <
			    s->running->sched.remaining_time)
			return true;
		if (s->alg_sched == P_PRIOR &&
		    node->pcb->sched.priority < s->running->sched.priority)
			return true;
	}
	return false;
}

void dispatch_save_ctx(struct Simulator *s)
{
	if (s->running == NULL)
		return;
	s->running->cpu_ctx = s->cpu_ctx;
	log_event(s, "DISPATCHER", "Contexto guardado de %s(%d): PC=%d.",
		  s->running->name, s->running->pid,
		  s->running->cpu_ctx.program_counter);
}

void dispatch_restore_ctx(struct Simulator *s, struct Pcb *p)
{
	if (p == NULL)
		return;
	s->cpu_ctx = p->cpu_ctx;
	log_event(s, "DISPATCHER", "Contexto restaurado de %s(%d): PC=%d.",
		  p->name, p->pid, p->cpu_ctx.program_counter);
}

void dispatch(struct Simulator *s)
{
	struct Pcb *next = s->next_pcb;
	struct SchedulerData *sched;

	if (next == NULL)
		return;
	s->next_pcb = NULL;
	s->switch_remaining = 0.0;
	s->running = next;
	dispatch_restore_ctx(s, next);
	set_process_state(s, next, RUNNING, "despachado a CPU");
	sched = &next->sched;
	if (sched->start_time < 0.0) {
		sched->start_time = s->current_time;
		sched->response_time = sched->start_time - sched->arrival_time;
	}
	if (s->alg_sched == ROUND && sched->remaining_quantum <= TIME_EPSILON)
		sched->remaining_quantum = s->quantum;
	s->cpu_busy = true;
}

void begin_context_switch(struct Simulator *s)
{
	if (s->next_pcb != NULL || q_empty(&s->ready_q))
		return;
	scheduler(s);
	if (s->next_pcb == NULL)
		return;
	s->next_pcb->sched.context_switches++;
	s->context_switch_count++;
	s->switch_remaining = s->switch_cost;
	if (s->switch_remaining <= TIME_EPSILON)
		dispatch(s);
}

void tick_running_process(struct Simulator *s, double delta)
{
	struct Pcb *p = s->running;
	double executed;

	if (p == NULL)
		return;
	p->sched.remaining_time -= delta;
	p->sched.cpu_time += delta;
	s->cpu_process_time += delta;
	s->cpu_ctx.program_counter++;
	if (s->alg_sched == ROUND)
		p->sched.remaining_quantum -= delta;

	executed = p->sched.cpu_time;
	while (p->interrupt.periodic_done < p->interrupt.periodic_target &&
	       executed + TIME_EPSILON >= p->interrupt.next_cpu_time) {
		enum IntType type = rand() % 100 < 70
			? INT_HW_TIMER : INT_SW_SYSCALL;
		record_interrupt(s, p, type, IO_NONE, false);
		p->interrupt.periodic_done++;
		p->interrupt.next_cpu_time =
			p->sched.burst_time * (p->interrupt.periodic_done + 1.0) /
			(p->interrupt.periodic_target + 1.0);
	}

	if (p->err.planned && !p->err.has_error &&
	    executed + TIME_EPSILON >= p->err.trigger_cpu_time) {
		if (p->err.planned_type == INT_EXC_DIV_ZERO)
			fail_running_process(s, INT_EXC_DIV_ZERO, "ERR_DIV_ZERO",
					     "División entre cero simulada");
		else
			fail_running_process(s, INT_EXC_MEM, "ERR_MEM_ACCESS",
					     "Acceso inválido a memoria simulada");
		return;
	}

	if (p->sched.remaining_time <= TIME_EPSILON) {
		terminate_running_process(s);
		return;
	}
	if (p->io.has_io && !p->io.started &&
	    executed + TIME_EPSILON >= p->io.start_time) {
		running_to_blocked(s);
		return;
	}
	if (s->alg_sched == ROUND &&
	    p->sched.remaining_quantum <= TIME_EPSILON) {
		record_interrupt(s, p, INT_HW_TIMER, IO_NONE, false);
		dispatch_save_ctx(s);
		p->sched.remaining_quantum = s->quantum;
		set_process_state(s, p, READY, "quantum agotado");
		enqueue(&s->ready_q, p);
		s->running = NULL;
		s->cpu_busy = false;
	}
}

struct GanttList gantt_init(void)
{
	struct GanttList gantt = {0};
	return gantt;
}

void update_gantt_interval(struct Simulator *s, enum GanttType type,
			   struct Pcb *p, double delta)
{
	struct GanttNode *tail = s->gantt.tail;
	int owner = -1;
	const char *name = "IDLE";

	if (type == GANTT_PROCESS && p != NULL) {
		owner = p->pid;
		name = p->name;
	} else if (type == GANTT_CONTEXT_SWITCH) {
		owner = -2;
		name = "CS";
	}
	if (tail != NULL && tail->type == type && tail->owner == owner) {
		tail->limit += delta;
		return;
	}
	tail = malloc(sizeof(*tail));
	if (tail == NULL)
		return;
	tail->start = s->current_time;
	tail->limit = s->current_time + delta;
	tail->type = type;
	tail->owner = owner;
	snprintf(tail->name, sizeof(tail->name), "%s", name);
	tail->next = NULL;
	if (s->gantt.tail == NULL)
		s->gantt.head = tail;
	else
		s->gantt.tail->next = tail;
	s->gantt.tail = tail;
	s->gantt.cont++;
}

void gantt_free(struct GanttList *g)
{
	struct GanttNode *node = g->head;
	while (node != NULL) {
		struct GanttNode *next = node->next;
		free(node);
		node = next;
	}
}

void tick_background(struct Simulator *s, double delta)
{
	int i;

	accumulate_queue_time(&s->ready_q, delta, 0);
	if (s->next_pcb != NULL)
		s->next_pcb->sched.ready_time += delta;
	for (i = 0; i < IO_DEVICE_COUNT; i++) {
		struct Node *node;
		accumulate_queue_time(&s->device_q[i], delta, 1);
		for (node = s->device_q[i].head; node != NULL; node = node->next)
			if (!node->pcb->resident)
				node->pcb->sched.nonresident_time += delta;
	}
	accumulate_queue_time(&s->nonresident_q, delta, 2);
	tick_device_queues(s, delta);
}

bool simulation_finished(struct Simulator *s)
{
	int i;

	if (!q_empty(&s->created_processes) || !q_empty(&s->job_q) ||
	    !q_empty(&s->ready_q) || !q_empty(&s->nonresident_q) ||
	    s->running != NULL || s->next_pcb != NULL)
		return false;
	for (i = 0; i < IO_DEVICE_COUNT; i++)
		if (!q_empty(&s->device_q[i]))
			return false;
	return s->user_process_count > 0;
}

void main_loop(struct Simulator *s)
{
	process_arrival(s);
	mid_term_scheduler(s);
	job_scheduler(s);
	mid_term_scheduler(s);
	job_scheduler(s);

	if (should_preempt(s)) {
		struct Pcb *p = s->running;
		dispatch_save_ctx(s);
		set_process_state(s, p, READY, "desalojo por planificador");
		enqueue(&s->ready_q, p);
		s->running = NULL;
		s->cpu_busy = false;
	}

	if (simulation_finished(s)) {
		s->state = SIM_STOP;
		log_event(s, "SIMULATOR", "Simulación terminada.");
		send_data(s, true);
		return;
	}

	if (s->next_pcb != NULL) {
		double delta = s->switch_remaining < TICK
			? s->switch_remaining : TICK;
		if (delta <= TIME_EPSILON) {
			dispatch(s);
		} else {
			update_gantt_interval(s, GANTT_CONTEXT_SWITCH, NULL, delta);
			s->current_time += delta;
			s->switch_remaining -= delta;
			s->context_switch_time += delta;
			tick_background(s, delta);
			if (s->switch_remaining <= TIME_EPSILON)
				dispatch(s);
			send_data(s, false);
			return;
		}
	}

	if (s->running == NULL && !q_empty(&s->ready_q)) {
		begin_context_switch(s);
		if (s->next_pcb != NULL) {
			double delta = s->switch_remaining < TICK
				? s->switch_remaining : TICK;
			update_gantt_interval(s, GANTT_CONTEXT_SWITCH, NULL, delta);
			s->current_time += delta;
			s->switch_remaining -= delta;
			s->context_switch_time += delta;
			tick_background(s, delta);
			if (s->switch_remaining <= TIME_EPSILON)
				dispatch(s);
			send_data(s, false);
			return;
		}
	}

	if (s->running == NULL) {
		update_gantt_interval(s, GANTT_IDLE, NULL, TICK);
		s->current_time += TICK;
		s->idle_time += TICK;
		tick_background(s, TICK);
		send_data(s, false);
		return;
	}

	update_gantt_interval(s, GANTT_PROCESS, s->running, TICK);
	s->current_time += TICK;
	tick_background(s, TICK);
	tick_running_process(s, TICK);
	mid_term_scheduler(s);

	if (simulation_finished(s)) {
		s->state = SIM_STOP;
		log_event(s, "SIMULATOR", "Simulación terminada.");
		send_data(s, true);
		return;
	}
	send_data(s, false);
}

void send_json_string(const char *text)
{
	const unsigned char *c = (const unsigned char *)text;
	putchar('"');
	while (*c != '\0') {
		switch (*c) {
		case '"': fputs("\\\"", stdout); break;
		case '\\': fputs("\\\\", stdout); break;
		case '\n': fputs("\\n", stdout); break;
		case '\r': fputs("\\r", stdout); break;
		case '\t': fputs("\\t", stdout); break;
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

/*
 * "texto escapado"
 */

static void send_interrupts(struct Pcb *p)
{
	int i;

	printf("\"interrupts\":{\"planned\":%d,\"periodic_completed\":%d,"
	       "\"total\":%d,\"by_type\":{",
	       p->interrupt.periodic_target, p->interrupt.periodic_done,
	       p->interrupt.total);
	for (i = 0; i < INT_TYPE_COUNT; i++) {
		if (i > 0)
			putchar(',');
		send_json_string(interrupt_type_name((enum IntType)i));
		printf(":%d", p->interrupt.by_type[i]);
	}
	printf("},\"history\":[");
	for (i = 0; i < p->interrupt.history_count; i++) {
		struct InterruptEvent *event = &p->interrupt.history[i];
		if (i > 0)
			putchar(',');
		printf("{\"type\":");
		send_json_string(interrupt_type_name(event->type));
		printf(",\"time\":%.3f,\"device\":", event->time);
		send_json_string(io_device_name(event->device));
		printf(",\"fatal\":%s}", event->fatal ? "true" : "false");
	}
	printf("]}");
}

/*
 * "interrupts": {
 *   "planned": 0,
 *   "periodic_completed": 0,
 *   "total": 0,
 *   "by_type": {
 *     "HW_IO": 0,
 *     "HW_TIMER": 0,
 *     "SW_SYSCALL": 0,
 *     "EXC_DIV_ZERO": 0,
 *     "EXC_MEMORY": 0
 *   },
 *   "history": [
 *     {
 *       "type": "HW_IO",
 *       "time": 0.000,
 *       "device": "DISK",
 *       "fatal": false
 *     }
 *   ]
 * }
 */

static void send_pcb(struct Pcb *p)
{
	printf("{\"pid\":%d,\"name\":", p->pid);
	send_json_string(p->name);
	printf(",\"state\":");
	send_json_string(process_state_name(p->state));
	printf(",\"is_system\":%s,\"resident\":%s,\"swap_count\":%d,"
	       "\"last_swap_out\":%.3f,\"last_swap_in\":%.3f,"
	       "\"cpu\":{\"program_counter\":%d,\"stack_pointer\":%d},"
	       "\"scheduler\":{\"arrival_time\":%.3f,\"burst_time\":%.3f,"
	       "\"remaining_time\":%.3f,\"start_time\":%.3f,\"finish_time\":%.3f,"
	       "\"turnaround_time\":%.3f,\"response_time\":%.3f,\"ready_time\":%.3f,"
	       "\"blocked_time\":%.3f,\"nonresident_time\":%.3f,"
	       "\"cpu_time\":%.3f,\"priority\":%d,\"remaining_quantum\":%.3f,"
	       "\"context_switches\":%d},"
	       "\"memory\":{\"required_kb\":%d,\"assigned_blocks\":%d,"
	       "\"waste_kb\":%d,\"start_block\":%d,\"limit_block\":%d,"
	       "\"block_address\":\"%p\"},"
	       "\"io\":{\"has_io\":%s,\"started\":%s,\"completed\":%s,"
	       "\"start_time\":%.3f,\"duration\":%.3f,\"remaining_time\":%.3f,"
	       "\"device\":",
	       p->is_system ? "true" : "false", p->resident ? "true" : "false",
	       p->swap_count, p->last_swap_out, p->last_swap_in,
	       p->cpu_ctx.program_counter, p->cpu_ctx.stack_pointer,
	       p->sched.arrival_time, p->sched.burst_time,
	       p->sched.remaining_time, p->sched.start_time,
	       p->sched.finish_time, p->sched.turnaround_time, p->sched.response_time,
	       p->sched.ready_time, p->sched.blocked_time,
	       p->sched.nonresident_time, p->sched.cpu_time,
	       p->sched.priority, p->sched.remaining_quantum,
	       p->sched.context_switches, p->mem.required_kb,
	       p->mem.assigned_blocks, p->mem.waste_kb,
	       p->mem.start, p->mem.limit, (void *)p->mem.block,
	       p->io.has_io ? "true" : "false",
	       p->io.started ? "true" : "false",
	       p->io.completed ? "true" : "false",
	       p->io.start_time, p->io.duration, p->io.remaining_time);
	send_json_string(io_device_name(p->io.device));
	printf("},");
	send_interrupts(p);
	printf(",\"error\":{\"planned\":%s,\"has_error\":%s,\"fatal\":%s,"
	       "\"occurred_at\":%.3f,\"code\":",
	       p->err.planned ? "true" : "false",
	       p->err.has_error ? "true" : "false",
	       p->err.fatal ? "true" : "false", p->err.occurred_at);
	send_json_string(p->err.error_code);
	printf(",\"description\":");
	send_json_string(p->err.error_desc);
	printf("}}");
}

/*
 * {
 *   "pid": 0,
 *   "name": "P0",
 *   "state": "READY",
 *   "is_system": false,
 *   "resident": true,
 *   "swap_count": 0,
 *   "last_swap_out": -1.000,
 *   "last_swap_in": -1.000,
 *   "cpu": {
 *     "program_counter": 0,
 *     "stack_pointer": 0
 *   },
 *   "scheduler": {
 *     "arrival_time": 0.000,
 *     "burst_time": 0.000,
 *     "remaining_time": 0.000,
 *     "start_time": -1.000,
 *     "finish_time": -1.000,
 *     "turnaround_time": 0.000,
 *     "response_time": 0.000,
 *     "ready_time": 0.000,
 *     "blocked_time": 0.000,
 *     "nonresident_time": 0.000,
 *     "cpu_time": 0.000,
 *     "priority": 0,
 *     "remaining_quantum": 0.000,
 *     "context_switches": 0
 *   },
 *   "memory": {
 *     "required_kb": 0,
 *     "assigned_blocks": 0,
 *     "waste_kb": 0,
 *     "start_block": -1,
 *     "limit_block": -1,
 *     "block_address": "0x0"
 *   },
 *   "io": {
 *     "has_io": false,
 *     "started": false,
 *     "completed": false,
 *     "start_time": 0.000,
 *     "duration": -1.000,
 *     "remaining_time": -1.000,
 *     "device": "NONE"
 *   },
 *   "interrupts": {
 *     "planned": 0,
 *     "periodic_completed": 0,
 *     "total": 0,
 *     "by_type": {},
 *     "history": []
 *   },
 *   "error": {
 *     "planned": false,
 *     "has_error": false,
 *     "fatal": false,
 *     "occurred_at": -1.000,
 *     "code": "",
 *     "description": ""
 *   }
 * }
 */

static void send_queue_processes(struct Queue *q, bool *first)
{
	struct Node *node;
	for (node = q->head; node != NULL; node = node->next) {
		if (!*first)
			putchar(',');
		send_pcb(node->pcb);
		*first = false;
	}
}

/*
 * Fragmento insertado dentro de un arreglo ya abierto:
 * { "pid": 0, "...": "campos de send_pcb" },
 * { "pid": 1, "...": "campos de send_pcb" }
 */

static void send_all_processes(struct Simulator *s)
{
	bool first = true;
	int i;

	putchar('[');
	send_queue_processes(&s->system_q, &first);
	send_queue_processes(&s->created_processes, &first);
	send_queue_processes(&s->job_q, &first);
	send_queue_processes(&s->ready_q, &first);
	for (i = 0; i < IO_DEVICE_COUNT; i++)
		send_queue_processes(&s->device_q[i], &first);
	send_queue_processes(&s->nonresident_q, &first);
	send_queue_processes(&s->finished_q, &first);
	if (s->running != NULL) {
		if (!first)
			putchar(',');
		send_pcb(s->running);
		first = false;
	}
	if (s->next_pcb != NULL) {
		if (!first)
			putchar(',');
		send_pcb(s->next_pcb);
	}
	putchar(']');
}

/*
 * [
 *   { "pid": 0, "...": "campos de send_pcb" },
 *   { "pid": 1, "...": "campos de send_pcb" }
 * ]
 */

static void send_pid_queue(struct Queue *q)
{
	struct Node *node;
	bool first = true;

	putchar('[');
	for (node = q->head; node != NULL; node = node->next) {
		if (!first)
			putchar(',');
		printf("%d", node->pcb->pid);
		first = false;
	}
	putchar(']');
}

/*
 * [0, 1, 2]
 */

static void send_queues(struct Simulator *s)
{
	int i;

	printf("\"queues\":{\"created\":");
	send_pid_queue(&s->created_processes);
	printf(",\"job\":");
	send_pid_queue(&s->job_q);
	printf(",\"ready\":");
	send_pid_queue(&s->ready_q);
	printf(",\"nonresident\":");
	send_pid_queue(&s->nonresident_q);
	printf(",\"finished\":");
	send_pid_queue(&s->finished_q);
	printf(",\"devices\":{");
	for (i = 0; i < IO_DEVICE_COUNT; i++) {
		if (i > 0)
			putchar(',');
		send_json_string(io_device_name((enum IoDevice)i));
		putchar(':');
		send_pid_queue(&s->device_q[i]);
	}
	printf("}}");
}

/*
 * "queues": {
 *   "created": [0],
 *   "job": [1],
 *   "ready": [2],
 *   "nonresident": [3],
 *   "finished": [4],
 *   "devices": {
 *     "KEYBOARD": [],
 *     "MOUSE": [],
 *     "DISK": [],
 *     "PRINTER": [],
 *     "NETWORK": []
 *   }
 * }
 */

static void send_memory(struct Simulator *s)
{
	struct MemoryBlock *block;
	bool first = true;

	printf("\"memory\":{\"total_kb\":%d,\"block_size_kb\":%d,"
	       "\"free_kb\":%d,\"os_reserved_kb\":%d,\"blocks\":[",
	       TOTAL_MEMORY_KB, BLOCK_SIZE_KB,
	       s->memory_list.free * BLOCK_SIZE_KB, OS_RESERVED_KB);
	for (block = s->memory_list.head; block != NULL; block = block->next) {
		if (!first)
			putchar(',');
		printf("{\"start_block\":%d,\"limit_block\":%d,"
		       "\"length_blocks\":%d,\"owner_pid\":",
		       block->start, block->limit, block->length);
		if (block->owner == NULL)
			printf("null,\"owner_name\":\"Libre\",\"is_system\":false}");
		else {
			printf("%d,\"owner_name\":", block->owner->pid);
			send_json_string(block->owner->name);
			printf(",\"is_system\":%s}",
			       block->owner->is_system ? "true" : "false");
		}
		first = false;
	}
	printf("]}");
}

/*
 * "memory": {
 *   "total_kb": 0,
 *   "block_size_kb": 0,
 *   "free_kb": 0,
 *   "os_reserved_kb": 0,
 *   "blocks": [
 *     {
 *       "start_block": 0,
 *       "limit_block": 0,
 *       "length_blocks": 0,
 *       "owner_pid": null,
 *       "owner_name": "Libre",
 *       "is_system": false
 *     }
 *   ]
 * }
 */

static void send_gantt(struct Simulator *s)
{
	struct GanttNode *node;
	bool first = true;

	printf("\"gantt\":{\"current_time\":%.3f,\"segments\":[", s->current_time);
	for (node = s->gantt.head; node != NULL; node = node->next) {
		if (!first)
			putchar(',');
		printf("{\"pid\":%d,\"name\":", node->owner);
		send_json_string(node->name);
		printf(",\"kind\":");
		send_json_string(gantt_type_name(node->type));
		printf(",\"start\":%.3f,\"limit\":%.3f,\"duration\":%.3f}",
		       node->start, node->limit, node->limit - node->start);
		first = false;
	}
	printf("]}");
}

/*
 * "gantt": {
 *   "current_time": 0.000,
 *   "segments": [
 *     {
 *       "pid": 0,
 *       "name": "P0",
 *       "kind": "PROCESS",
 *       "start": 0.000,
 *       "limit": 0.000,
 *       "duration": 0.000
 *     }
 *   ]
 * }
 */

static void send_stats(struct Simulator *s)	/* Promedio */
{
	struct Node *node;
	double waiting = 0.0;
	double turnaround = 0.0;
	double response = 0.0;
	int measured = 0;

	for (node = s->finished_q.head; node != NULL; node = node->next) {
		struct Pcb *p = node->pcb;
		waiting += p->sched.ready_time;
		turnaround += p->sched.turnaround_time;
		response += p->sched.response_time;
		measured++;
	}
	printf("\"stats\":{\"avg_waiting\":%.3f,\"avg_turnaround\":%.3f,"
	       "\"avg_response\":%.3f,\"throughput\":%.6f,\"cpu_util\":%.3f,"
	       "\"total_time\":%.3f,\"completed\":%d,\"errors\":%d,"
	       "\"interrupts\":%d,\"swap_outs\":%d,\"swap_ins\":%d,"
	       "\"context_switches\":%d,\"context_switch_time\":%.3f}",
	       measured == 0 ? 0.0 : waiting / measured,
	       measured == 0 ? 0.0 : turnaround / measured,
	       measured == 0 ? 0.0 : response / measured,
	       s->current_time <= 0.0 ? 0.0 :
		       s->completed_count / s->current_time,
	       s->current_time <= 0.0 ? 0.0 :
		       s->cpu_process_time / s->current_time * 100.0,
	       s->current_time, s->completed_count, s->error_count,
	       s->interrupt_count, s->swap_out_count, s->swap_in_count,
	       s->context_switch_count, s->context_switch_time);
}

/*
 * "stats": {
 *   "avg_waiting": 0.000,
 *   "avg_turnaround": 0.000,
 *   "avg_response": 0.000,
 *   "throughput": 0.000000,
 *   "cpu_util": 0.000,
 *   "total_time": 0.000,
 *   "completed": 0,
 *   "errors": 0,
 *   "interrupts": 0,
 *   "swap_outs": 0,
 *   "swap_ins": 0,
 *   "context_switches": 0,
 *   "context_switch_time": 0.000
 * }
 */

void send_data(struct Simulator *s, bool force)
{
	int64_t now = monotonic_ms();

	if (!force && s->last_snapshot_ms > 0 &&
	    now - s->last_snapshot_ms < SNAPSHOT_INTERVAL_MS)
		return;
	s->last_snapshot_ms = now;
	s->snapshot_sequence++;

	printf("SIM_DATA {\"type\":\"state\",\"sequence\":%llu,"
	       "\"current_time\":%.3f,\"simulator_state\":%d,"
	       "\"cpu_busy\":%s,\"running_pid\":",
	       (unsigned long long)s->snapshot_sequence, s->current_time,
	       s->state, s->cpu_busy ? "true" : "false");
	if (s->running == NULL)
		printf("null");
	else
		printf("%d", s->running->pid);
	printf(",\"dispatching_pid\":");
	if (s->next_pcb == NULL)
		printf("null");
	else
		printf("%d", s->next_pcb->pid);
	printf(",\"config\":{\"scheduler_algorithm\":%d,\"scheduler_name\":",
	       s->alg_sched);
	send_json_string(scheduler_algorithm_name(s->alg_sched));
	printf(",\"memory_algorithm\":%d,\"memory_name\":", s->alg_memory);
	send_json_string(memory_algorithm_name(s->alg_memory));
	printf(",\"quantum\":%.3f,\"switch_cost\":%.3f,"
	       "\"snapshot_interval_ms\":%d},\"processes\":",
	       s->quantum, s->switch_cost, SNAPSHOT_INTERVAL_MS);
	send_all_processes(s);
	putchar(',');
	send_queues(s);
	putchar(',');
	send_memory(s);
	putchar(',');
	send_gantt(s);
	putchar(',');
	send_stats(s);
	printf("}\n");
	fflush(stdout);
}

/*
 * SIM_DATA {
 *   "type": "state",
 *   "sequence": 0,
 *   "current_time": 0.000,
 *   "simulator_state": 0,
 *   "cpu_busy": false,
 *   "running_pid": null,
 *   "dispatching_pid": null,
 *   "config": {
 *     "scheduler_algorithm": 0,
 *     "scheduler_name": "FCFS",
 *     "memory_algorithm": 0,
 *     "memory_name": "First Fit",
 *     "quantum": 0.000,
 *     "switch_cost": 0.000,
 *     "snapshot_interval_ms": 0
 *   },
 *   "processes": [
 *     { "pid": 0, "...": "campos de send_pcb" }
 *   ],
 *   "queues": {
 *     "...": "campos de send_queues"
 *   },
 *   "memory": {
 *     "...": "campos de send_memory"
 *   },
 *   "gantt": {
 *     "...": "campos de send_gantt"
 *   },
 *   "stats": {
 *     "...": "campos de send_stats"
 *   }
 * }
 */

static bool valid_config(int sched, int memory, double quantum, double cost)
{
	if (sched < FCFS || sched > P_PRIOR || memory < FIRST || memory > WORST)
		return false;
	if (quantum < 0.0 || cost < 0.0 || cost > 100.0)
		return false;
	if (sched == ROUND && quantum <= 0.0)
		return false;
	return true;
}

void process_stdin(struct Simulator *s, char *line)
{
	if (strncmp(line, "CONFIG", 6) == 0) {
		int sched;
		int memory;
		double quantum;
		double cost;
		int parsed = sscanf(line, "CONFIG %d %d %lf %lf",
				    &sched, &memory, &quantum, &cost);
		if (parsed != 4 || !valid_config(sched, memory, quantum, cost)) {
			log_event(s, "ERROR", "CONFIG inválido: %s", line);
			return;
		}
		s->alg_sched = (enum AlgorithmSched)sched;
		s->alg_memory = (enum AlgorithmMem)memory;
		s->quantum = quantum;
		s->switch_cost = cost;
		log_event(s, "CONFIG",
			  "Planificador=%s, memoria=%s, quantum=%.2f, cambio=%.2f.",
			  scheduler_algorithm_name(s->alg_sched),
			  memory_algorithm_name(s->alg_memory),
			  s->quantum, s->switch_cost);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "ADD", 3) == 0) {
		char name[16];
		int mem_kb;
		double burst;
		double arrival;
		int priority;
		struct Pcb *p;
		int parsed = sscanf(line, "ADD %15s %d %lf %lf %d",
				    name, &mem_kb, &burst, &arrival, &priority);
		if (parsed != 5 || mem_kb <= 0 || burst <= 0.0 ||
		    arrival < 0.0 || priority < 0 || priority > 99) {
			log_event(s, "ERROR", "ADD inválido: %s", line);
			return;
		}
		p = malloc(sizeof(*p));
		if (p == NULL) {
			fprintf(stderr, "OOM al crear proceso.\n");
			return;
		}
		*p = create_user_pcb(s, name, mem_kb, burst, arrival, priority);
		enqueue(&s->created_processes, p);
		log_event(s, "PROCESS", "%s(%d) creado.", p->name, p->pid);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "RANDOM", 6) == 0) {
		create_random_processes(s);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "SPEED", 5) == 0) {
		int speed;
		if (sscanf(line, "SPEED %d", &speed) != 1 ||
		    speed < 1 || speed > 100) {
			log_event(s, "ERROR", "SPEED inválido: %s", line);
			return;
		}
		s->sim_speed = speed;
		return;
	}

	if (strncmp(line, "RUN", 3) == 0) {
		s->state = SIM_RUN;
		log_event(s, "SIMULATOR", "Simulación iniciada.");
		send_data(s, true);
		return;
	}
	if (strncmp(line, "PAUSE", 5) == 0) {
		s->state = SIM_PAUSE;
		log_event(s, "SIMULATOR", "Simulación pausada.");
		send_data(s, true);
		return;
	}
	if (strncmp(line, "STOP", 4) == 0) {
		s->state = SIM_STOP;
		log_event(s, "SIMULATOR", "Simulación detenida.");
		send_data(s, true);
		return;
	}
	log_event(s, "ERROR", "Comando desconocido: %s", line);
}

bool stdin_has_data(void)
{
	struct pollfd fd = {0};
	fd.fd = STDIN_FILENO;
	fd.events = POLLIN;
	return poll(&fd, 1, 0) > 0 &&
	       (fd.revents & (POLLIN | POLLHUP | POLLERR | POLLNVAL));
}

static struct Simulator simulator_init(void)
{
	struct Simulator s;
	int i;

	memset(&s, 0, sizeof(s));
	s.state = SIM_PAUSE;
	s.alg_sched = FCFS;
	s.alg_memory = FIRST;
	s.quantum = 1.0;
	s.switch_cost = 0.5;
	s.sim_speed = 5;
	s.next_pid = RESERVED_PID_COUNT;
	s.system_q = init_queue();
	s.created_processes = init_queue();
	s.job_q = init_queue();
	s.ready_q = init_queue();
	s.nonresident_q = init_queue();
	s.finished_q = init_queue();
	for (i = 0; i < IO_DEVICE_COUNT; i++)
		s.device_q[i] = init_queue();
	s.memory_list = mem_init();
	s.gantt = gantt_init();
	create_system_processes(&s);
	return s;
}

static void simulator_free(struct Simulator *s)
{
	if (s->running != NULL)
		free(s->running);
	if (s->next_pcb != NULL)
		free(s->next_pcb);
	q_free(&s->system_q);
	q_free(&s->created_processes);
	q_free(&s->job_q);
	q_free(&s->ready_q);
	for (int i = 0; i < IO_DEVICE_COUNT; i++)
		q_free(&s->device_q[i]);
	q_free(&s->nonresident_q);
	q_free(&s->finished_q);
	
	memory_free_all(&s->memory_list);
	gantt_free(&s->gantt);
}

static void demo(struct Simulator *s)
{
	
}

int main(void)
{
	struct Simulator simulator;
	char line[256];

	srand((unsigned int)time(NULL));
	simulator = simulator_init();
	setvbuf(stdin, NULL, _IONBF, 0);
	setvbuf(stdout, NULL, _IOLBF, 0);
	send_data(&simulator, true);

	while (simulator.state != SIM_STOP) {
		usleep((useconds_t)(TICK_US / simulator.sim_speed));
		while (stdin_has_data()) {
			if (fgets(line, sizeof(line), stdin) == NULL) {
				if (simulator.state == SIM_PAUSE)
					simulator.state = SIM_STOP;
				break;
			}
			process_stdin(&simulator, line);
			if (simulator.state == SIM_STOP)
				break;
		}
		if (simulator.state == SIM_RUN)
			main_loop(&simulator);
	}
	simulator_free(&simulator);
	return EXIT_SUCCESS;
}

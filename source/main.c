#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define TICK		0.1	/* Cuanto avanza (u.t.) en cada iteracion */
#define TICK_MS		50000	/* MS = MICROSEGUNDOS, 1000 MS = 1 Milisegundo */

#define TOTAL_BLOCKS	1024
#define BLOCK_SIZE      4    	/* Tamaño de cada bloque      */

#define ERR_CODE_MAX    16   	/* Máximo tamaño de codigo de error      */
#define ERR_DESC_MAX    32   	/* Máximo tamaño de descripción de error */

#define PCB_CANT	10

enum AlgorithmSched {
	FCFS		= 0,
	NP_SJF		= 1,
	P_SJF		= 2,
	NP_ROUND	= 3,
	P_ROUND		= 4,
	NP_PRIOR	= 5,
	P_PRIOR		= 6
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
	double quantum_remaining;
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
	/* Scheduler largo plazo */
	struct Queue process_q;
	struct Queue ready_q;
	struct Queue io_q;
	struct Queue finished_q;
	
	struct MemoryBlockList memory_list;
	enum AlgorithmMem alg_memory;
	
	/* Estado CPU */
	struct Pcb *running;
	bool cpu_busy;
	
	/* Dispatcher */
	struct ContextList context_list;

	enum AlgorithmSched alg_sched;
	
	double current_time;
	
	int next_pid;
	
	int total_created;
};

/* Algoritmos de colas */
struct Queue init_queue(void)
{
	struct Queue q;
	
	q.cont = 0;
        q.head = NULL;
        q.tail = NULL;
	
	return q;
}

bool q_empty(struct Queue *q)
{
    return q->tail == NULL;
}

/*  Encola en head y crece hacia la derecha (tail)
 *  head -> p0 -> p1 -> p2 <- tail
 */
void enqueue(struct Queue *q, struct Pcb *p)
{
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

/* Solo se usa si (q->cont == 1), o sea queda UN solo elemento. */
struct Pcb *dequeue_last(struct Queue *q)
{
	struct Node *tmp = q->head;
	struct Pcb *p = tmp->pcb;
	
	q->cont = 0;
	q->head = NULL;
	q->tail = NULL;
	
	free(tmp);
	
	return p;
}

/* Devuelve el nodo más antiguo (primero en llegar) */
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

/* Solo si el PCB existe */
void dequeue_pcb(struct Queue *q, struct Pcb *p)
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

void q_free(struct Queue *q)
{
	while(!q_empty(q)) {
		free(q->head->pcb);
		dequeue_head(q);
	}
}

/* Implementación - Lista de Memoria */
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
		} else {
			tmp = tmp->next;
		}
	}

	update_max_mem(m);
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

bool enqueue_block(struct MemoryBlockList *m,
		   struct MemoryBlock *curr, struct MemoryBlock *ant,
		   struct Pcb *p, const int blocks_needed)
{
	struct MemoryBlock *mb = malloc(sizeof(struct MemoryBlock));

	if (!mb) {
		fprintf(stderr, "OOM en enqueue_block.\n");
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
	
	curr->start = mb->limit;
	curr->length = curr->limit - curr->start;
	
	if (curr == m->max)
		update_max_mem(m);
	
	/* Asignar valores en PCB */
	p->mem.start = mb->start;
	p->mem.limit = mb->limit;
	p->mem.assigned_blocks = blocks_needed;
	p->mem.waste_kb = blocks_needed * BLOCK_SIZE - p->mem.required_kb;

	m->free -= blocks_needed;
	m->cont++;

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
				return enqueue_block(m, tmp, tmp_ant, p, blocks_needed);
			
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

		return enqueue_block(m, best, best_ant, p, blocks_needed);
	}

	if (alg == WORST) {
		struct MemoryBlock *worst = m->max;
		struct MemoryBlock *worst_ant = m->head;

		if (worst == m->head)
			return enqueue_block(m, worst, NULL, p, blocks_needed);

		while (worst_ant->next != worst)
			worst_ant = worst_ant->next;

		return enqueue_block(m, worst, worst_ant, p, blocks_needed);
	}

	return false;
}

/* Implementación - Process Control Block (PCB) */
struct Pcb create_pcb(struct Simulator *s, char *name, int mem_kb,
		      double burst, double arrival,
		      int priority, double quantum)
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
	p.sched.quantum_remaining	= quantum;

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
	
	s->total_created++;

	return p;
}

/* Dispatcher */
struct ContextList ctx_init(void) // head -> cn -> ... -> c1 -> c0 -> NULL
{
	struct ContextList ctx;

	ctx.count = 0;
	ctx.head = NULL;

	return ctx;
}

void dispatch_save_ctx(struct Simulator *s)
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
		fprintf(stderr, "OOM en save_ctx\n");
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

void dispatch(struct Simulator *s, struct Pcb *p)
{
	dispatch_save_ctx(s);
	
	p->state = RUNNING;
	
	s->running = p;
	s->cpu_busy = true;
}

/* Scheduler */
void admit_ready_q(struct Simulator *s)
{
	struct Queue *pq = &s->process_q;
	struct Queue *rq = &s->ready_q;
	struct Node *tmp = pq->head;

	while (tmp != NULL) {
		struct Pcb *p = tmp->pcb;
		
		tmp = tmp->next;
		
		/* Para procesos nuevos (NEW) */
		if (p->state == NEW && p->sched.arrival_time <= s->current_time) {
			if (!kmalloc(s, p))
				continue;
			
			p->state = READY;
			
			enqueue(rq, p);
			dequeue_pcb(pq, p);
		}
	}
}

struct Pcb *alg_fcfs(struct Simulator *s)
{
	return dequeue_head(&(s->ready_q));
}

struct Pcb *alg_np_sjf(struct Simulator *s)
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

struct Pcb *alg_p_sjf(struct Simulator *s) {
	struct Queue *rq = &s->ready_q;
	struct Node *tmp = rq->head;
	struct Pcb *p = tmp->pcb;

	tmp = tmp->next;

	while (tmp != NULL) {

	}
}

void scheduler(struct Simulator *s)
{
	enum AlgorithmSched alg = s->alg_sched;
	struct Pcb *p;

	if (alg == FCFS) {
		p = alg_fcfs(s);
		dispatch(s, p);
		return;
	}

	if (alg == NP_SJF) {
		p = alg_np_sjf(s);
		dispatch(s, p);
		return;
	}
	
	if (alg == P_SJF) {
		
	}

	if (alg == NP_ROUND) {

	}
	
	if (alg == P_ROUND) {

	}
	
	if (alg == NP_PRIOR) {

	}
	
	if (alg == P_PRIOR) {

	}
}

/* Simulador oekwokeowkeokwoekowekowkeowkeowkeowkeokw */
struct Simulator simulator_init(void)
{
	struct Simulator s;
	
	s.process_q	= init_queue();
	s.ready_q	= init_queue();
	s.io_q		= init_queue();
	s.finished_q	= init_queue();
	
	s.memory_list	= mem_init();
	
	s.context_list	= ctx_init();
	
	s.running	= NULL;
	s.cpu_busy	= false;
	
	s.current_time	= 0;
	
	s.next_pid	= 0;

	s.total_created	= 0;

	return s;
}

/* Print functions */
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
		
	printf("\nprocess_q:\n");
	printf("%-6s %-5s %-9s %-6s %-10s %-9s %-9s %-8s %-8s\n", "Name", "Pid", "Mem_req", "Burst", "Remaining", "Arrival", "B_needed", "Blocks", "Waste(kb)");
	print_queue(&s->process_q);
	
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

int main(void)
{
	struct Simulator simulator = simulator_init();
	struct Simulator *s = &simulator;

	s->alg_sched = NP_SJF;
	s->alg_memory = BEST;
	
	srand(time(NULL));

	for (int i = 0; i < PCB_CANT; i++) {
		float burst_time	= 1 + rand() % 9;
		float arrival_time	= 1 + rand() % 9;
		int memory		= 512 + rand() % 1023;
		char name[3];
		
		snprintf(name, sizeof(name), "P%d", i);

		struct Pcb *pcb = malloc(sizeof(struct Pcb));
		*pcb = create_pcb(s, name, memory, burst_time, arrival_time, -1, -1);
		
		enqueue(&s->process_q, pcb);
	}

	printf("\033[?25l");
	while (true) {
		usleep(TICK_MS);
		s->current_time += TICK;
		
		/* Si terminaron todos los procesos */
		if (s->process_q.cont == 0 && s->ready_q.cont == 0 && s->running == NULL) {
			break;
		}

		/* Si existen procesos NO listos, se agregan a listos */
		if (s->process_q.cont > 0) {
			admit_ready_q(s);
		}

		if (s->ready_q.cont > 0 && !s->cpu_busy) {
			scheduler(s);
		}

		if (s->running != NULL) {
			s->running->sched.remaining_time -= TICK;

			if (s->running->sched.remaining_time <= 0) {
				s->running->sched.remaining_time = 0;
				s->running->state = TERMINATED;

				enqueue(&s->finished_q, s->running);
				kfree(&s->memory_list, s->running);

				s->running = NULL;
				s->cpu_busy = false;
			}
		}

		/* Imprimir */
		print_main_loop(s);
	}
	printf("\033[?25h");

	q_free(&s->finished_q);

	return 0;
}
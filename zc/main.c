#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <stdbool.h>
#include <unistd.h>
#include <string.h>

#define TOTAL_BLOCKS    1024	/* Bloques totales en memoria */
#define BLOCK_SIZE      4    	/* Tamaño de cada bloque      */

#define ERR_CODE_MAX    16   	/* Máximo tamaño de codigo de error      */
#define ERR_DESC_MAX    32   	/* Máximo tamaño de descripción de error */

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
	char	name[16];
	int	pid;
	
	enum ProcessState	state;
	struct CpuContext	cpu_ctx;
	struct MemoryData	mem;
	struct SchedulerData	sched;
	struct IoData		io;
	struct ErrorData	err;
	
	struct Interrupt	interrupt;
};

struct Node {
	struct Pcb   pcb;
	struct Node *next;
};

struct Queue {
	int cont;
	struct Node *head;
	struct Node *tail;
};

struct Block {
	int start;
	int limit;
	int length;
	int owner;
	
	struct Block *next;
};

struct MemoryList {
	int cont;

	struct Block *head;
	struct Block *tail;
	
	struct Block *max; /* Puntero al mayor espacio libre */
	int free;
};

struct Simulator {
	/* Scheduler largo plazo */
	struct Queue process_q;
	struct Queue ready_q;
	struct Queue io_q;
	struct Queue finished_q;
	
	struct MemoryList memory_list;
	
	/* Estado CPU */
	struct Pcb  *running;
	bool         cpu_busy;
	
	/* Dispatcher */
	struct CpuContext *saved_contexts;
	int *saved_pids;
	int  ctx_count;
	
	double	current_time;
	
	int 	next_pid;
	
	int	total_created;
};

/* Declarar funciones */
void print_pcb(struct Pcb *);

/* Algoritmos de colas */
struct Queue init_queue()
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
	
	node->pcb = *p;
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
struct Pcb dequeue_last(struct Queue *q)
{
	struct Node *tmp = q->head;
	struct Pcb p = tmp->pcb;
	
	q->cont = 0;
	q->head = NULL;
	q->tail = NULL;
	
	free(tmp);
	
	return p;
}

/* Devuelve el nodo más antiguo (primero en llegar) */
struct Pcb dequeue_head(struct Queue *q)
{
	if (q->cont == 1)
		return dequeue_last(q);
	
	struct Node *old_head = q->head;
	struct Pcb p = old_head->pcb;
	
	q->head = q->head->next;
	q->cont--;
	
	free(old_head);
	
	return p;
}

struct Pcb dequeue_tail(struct Queue *q)
{
	if (q->cont == 1)
		return dequeue_last(q);
	
	struct Node *old_tail = q->tail;
	struct Node *tmp = q->head;
	struct Pcb p = old_tail->pcb;

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
	int pid = p->pid;
	
	if (q->tail->pcb.pid == pid) {
		dequeue_tail(q);
		return;
	}
	
	if (q->head->pcb.pid == pid) {
		dequeue_head(q);
		return;
	}
	
	struct Node *tmp_back = q->head;
	
	while (tmp_back->next->pcb.pid != pid)
		tmp_back = tmp_back->next;
	
	struct Node *tmp_pcb = tmp_back->next;
	tmp_back->next = tmp_pcb->next;
	
	q->cont--;
	
	free(tmp_pcb);
}

void print_queue(struct Queue *q)
{
	struct Node *tmp = q->head;
	
	while (tmp != NULL) {
		print_pcb(&tmp->pcb);
		tmp = tmp->next;
	}
	
	free(tmp);
}

void q_free(struct Queue *q)
{
	while(!q_empty(q))
		dequeue_tail(q);
}

/* Implementación - Lista de Memoria */
struct MemoryList mem_init()
{
	struct MemoryList m;
	struct Block *fb = malloc(sizeof(struct Block));
	
	if (!fb) {
		fprintf(stderr, "OOM en mem_init.\n");
		exit(1);
	}
	
	fb->start  = 0;
	fb->limit  = TOTAL_BLOCKS;
	fb->length = TOTAL_BLOCKS;
	fb->owner  = -1;
	fb->next   = NULL;
	
	m.cont = 1;
	m.head = fb;
	m.tail = fb;
	m.max  = fb;
	m.free	   = TOTAL_BLOCKS;
	
	return m;
}

void update_max_mem(struct MemoryList *m)
{
	struct Block *tmp = m->head;
	
	while (tmp != NULL) {
		if (tmp->owner == -1 && tmp->length > m->max->length)
			m->max = tmp;
		
		tmp = tmp->next;
	}
}

void kfree(struct MemoryList *m, struct Pcb *p)
{
	struct Block *tmp = m->head;

	while (tmp != NULL) {
		if (tmp->owner == p->pid) {
			tmp->owner = -1;
			return;
		}

		tmp = tmp->next;
	}
}

bool kmalloc(struct MemoryList *m, struct Pcb *p)
{
	int blocks_needed = (p->mem.required_kb + BLOCK_SIZE - 1) / BLOCK_SIZE;
	
	/* En caso el proceso exceda la memoria del simulador */
	if (blocks_needed > TOTAL_BLOCKS) {
		fprintf(stderr, "OOM en kmalloc: Proceso demasiado grande.");
		exit(1);
	}

	/* En caso no haya espacio actualmente */
	if (blocks_needed > m->max->length)
		return false;

	struct Block *tmp = m->head;
	struct Block *tmp_ant = NULL;

	while (tmp != NULL) {
		if (tmp->owner == -1 && blocks_needed <= tmp->length) {
			struct Block *fb = malloc(sizeof(struct Block));
			
			fb->start = tmp->start;
			fb->limit = tmp->start + blocks_needed;
			fb->length = blocks_needed;
			fb->owner = p->pid;
			fb->next = tmp;
			
			if (tmp_ant != NULL) {
				tmp_ant->next = fb;
			} else {
				m->head = fb;
			}

			tmp->start = fb->limit;
			tmp->length = tmp->limit - tmp->start;
			
			if (tmp == m->max)
				update_max_mem(m);

			/* Asignar valores en PCB */
			p->mem.start = fb->start;
			p->mem.limit = fb->limit;
			p->mem.assigned_blocks = blocks_needed;
			p->mem.waste_kb = blocks_needed * BLOCK_SIZE - p->mem.required_kb;
				
			m->cont++;
				
			return true;
		}
		
		tmp_ant = tmp;
		tmp = tmp->next;
	}

	return false;
}

void kmerge(struct MemoryList *m)
{
	struct Block *tmp = m->head;

	while (tmp->next != NULL) {
		if (tmp->owner == -1 && tmp->next->owner == -1) {
			struct Block *to_free = tmp->next;

			tmp->limit = tmp->next->limit;
			tmp->length = tmp->limit - tmp->start;
			tmp->next = to_free->next;

			free(to_free);
		} else {
			tmp = tmp->next;
		}
	}
}

void print_memory(struct MemoryList *m) {
	struct Block *tmp = m->head;

	while (tmp != NULL) {
		printf("[%d] -> ", tmp->owner);
		tmp = tmp->next;
	}

	printf("NULL\n");

	tmp = m->head;

	while (tmp != NULL) {
		printf(" %d    ", tmp->start);
		tmp = tmp->next;
	}

	printf("1024\n");
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
	double factor = (burst / 100 + mem_kb / 1024) * 7.5; /* Rango: Burst 1-100 | Mem 1-1024 */
		
	p.interrupt.int_count     = 5 + (int)(factor);
		
	if (p.interrupt.int_count > 20)
		p.interrupt.int_count = 20;
		
	p.interrupt.int_done      = 0;
	p.interrupt.next_int      = burst * (0.1 + (rand() % 80) / 100.0); /* Primera interrupcion a 10-90 % del burst */
	
	s->total_created++;

	return p;
}

void print_pcb(struct Pcb *p)
{
	printf("NAME: %s | PID: %d | Mem_req: %d | Burst: %.2f | Arrival: %.2f |, Blocks Needed: %d | Blocks: %d\n",
		p->name, p->pid, p->mem.required_kb, p->sched.burst_time, p->sched.arrival_time,
		(p->mem.required_kb + BLOCK_SIZE - 1) / BLOCK_SIZE, p->mem.assigned_blocks);
}

/* Dispatcher */
void dispatch_save_context(struct Simulator *s, struct Pcb *p)
{
	s->saved_contexts = realloc(s->saved_contexts, sizeof(struct CpuContext) * (s->ctx_count + 1));
	s->saved_pids     = realloc(s->saved_pids, sizeof(int) * (s->ctx_count + 1));
	
	if (!s->saved_contexts || !s->saved_pids) {
		fprintf(stderr, "OOM en dispatch_save_context.\n");
		exit(1);
	}
	
	s->saved_contexts[s->ctx_count] = p->cpu_ctx;
	s->saved_pids    [s->ctx_count] = p->pid;
	s->ctx_count++;
}

/* Scheduler */
void admit_ready_q(struct Simulator *s)
{
	struct Queue *pq = &s->process_q;
	struct Queue *rq = &s->ready_q;
	struct MemoryList *m = &s->memory_list;

	struct Node *tmp = pq->head;
	
	while (tmp != NULL) {
		struct Pcb *p = &tmp->pcb;
		
		tmp = tmp->next;

		/* Para procesos nuevos (NEW) */
		if (p->state == NEW && p->sched.arrival_time <= s->current_time) {
			if (!kmalloc(m, p))
				continue;
			
			p->state = READY;
			
			enqueue(rq, p);
			dequeue_pcb(pq, p);
		}
	}
}

struct Pcb fcfs_sched(struct Simulator *s)
{
	return dequeue_head(&(s->ready_q));
}

struct Simulator simulator_init()
{
	struct Simulator s;
	
	s.process_q	= init_queue();
	s.ready_q	= init_queue();
	s.io_q		= init_queue();
	s.finished_q	= init_queue();
	
	s.memory_list	= mem_init();
	
	s.running 	= NULL;
	s.cpu_busy 	= false;
	
	s.saved_contexts = malloc(sizeof(struct CpuContext));
	s.saved_pids     = malloc(sizeof(int));
	s.ctx_count      = 0;
	
	s.current_time = 0;
	
	s.next_pid = 0;

	s.total_created = 0;

	return s;
}

int main() {
	char *name = malloc(sizeof(char) * 3);
	int memory;
	float burst_time;
	float arrival_time;
	int pcb_cant = 10;
	
	name[0] = 'P';
	name[2] = '\0';

	struct Simulator simulator = simulator_init();
	
	for (int i = 0; i < pcb_cant; i++) {
		name[1]		= i + '0';
		memory		= 1 + rand() % 1023;
		burst_time	= 1 + rand() % 99;
		arrival_time	= 1 + rand() % 49;
		
		struct Pcb pcb = create_pcb(&simulator, name, memory, burst_time, arrival_time, -1, -1);
		
		enqueue(&simulator.process_q, &pcb);
	}
	
	printf("\nProcess_q:\n");
	print_queue(&simulator.process_q);

	admit_ready_q(&simulator);
	printf("\nadmit_ready_q\n");
	
	printf("\nReady_q:\n");
	print_queue(&simulator.ready_q);

	printf("\nMemory List:\n");
	print_memory(&simulator.memory_list);

	return 0;
}
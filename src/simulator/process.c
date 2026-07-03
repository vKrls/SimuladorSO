#include "process.h"

#include "dispatcher.h"
#include "interrupt.h"
#include "memory.h"
#include "names.h"
#include "queue.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static struct Pcb pcb_defaults(void)
{
	struct Pcb p;

	memset(&p, 0, sizeof(p));

	p.cpu_ctx.stack_pointer = -1;
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

static int interrupt_target_for(int mem_kb, double burst)
{
	double memory_factor = (double)mem_kb / (192.0 * 1024.0);
	double burst_factor = burst / 30.0;
	int target = 5 + (int)(((memory_factor + burst_factor) / 2.0) * 15.0);

	if (target < 5)
		return 5;
	if (target > 20)
		return 20;
	return target;
}

struct Pcb create_user_pcb(struct Simulator *s, const char *name, int mem_kb,
			   double burst, double arrival, int priority)
{
	struct Pcb p = pcb_defaults();

	snprintf(p.name, sizeof(p.name), "%s", name);
	p.pid = s->next_pid++;
	p.state = NEW;

	p.mem.required_kb = mem_kb;
	
	p.sched.arrival_time = arrival;
	p.sched.burst_time = burst;
	p.sched.remaining_time = burst;
	p.sched.priority = priority;
	p.sched.remaining_quantum = s->quantum;

	/* Entrada y Salida */
	p.io.has_io = rand() % 100 < 65;
	p.io.start_time = burst * (0.15 + (rand() % 66) / 100.0);
	if (p.io.has_io) {
		p.io.duration = 0.5 + (rand() % 76) / 10.0;
		p.io.remaining_time = p.io.duration;
		p.io.device = (enum IoDevice)(rand() % IO_DEVICE_COUNT);
	}

	/* Interrupciones en base a la memoria y burst */
	p.interrupt.periodic_target = interrupt_target_for(mem_kb, burst);
	p.interrupt.next_cpu_time = burst / (p.interrupt.periodic_target + 1.0);

	/* Errores (0.5 %) */
	p.err.planned = rand() % 1000 < 5;
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
	for (int i = 0; i < s->random_process_count; i++) {
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

void demo(struct Simulator *s)
{
	static const struct {
		const char *name;
		int memory_kb;
		double burst;
		double arrival;
		int priority;
		bool has_io;
		double io_start;
		double io_duration;
		enum IoDevice device;
	} demos[] = {
	/*	 Name,  Memory,     Burst, Arrival, Priority, Has_io, Io_start, Io_duration, Device */
		{"D00", 32  * 1024, 8.0,   0.0,     2,        true,   2.0,      1.5,         IO_DISK},
		{"D01", 48  * 1024, 12.0,  0.0,     4,        false,  0.0,      0.0,         IO_NONE},
		{"D02", 24  * 1024, 5.0,   1.0,     1,        true,   1.5,      0.8,         IO_KEYBOARD},
		{"D03", 96  * 1024, 18.0,  1.0,     7,        true,   6.0,      2.5,         IO_NETWORK},
		{"D04", 64  * 1024, 10.0,  2.0,     3,        false,  0.0,      0.0,         IO_NONE},
		{"D05", 40  * 1024, 7.0,   2.0,     5,        true,   2.5,      1.2,         IO_PRINTER},
		{"D06", 128 * 1024, 22.0,  3.0,     8,        true,   8.0,      3.0,         IO_DISK},
		{"D07", 56  * 1024, 9.0,   3.0,     0,        false,  0.0,      0.0,         IO_NONE},
		{"D08", 72  * 1024, 14.0,  4.0,     6,        true,   5.0,      1.7,         IO_MOUSE},
		{"D09", 28  * 1024, 6.0,   4.0,     2,        false,  0.0,      0.0,         IO_NONE},
		{"D10", 144 * 1024, 25.0,  5.0,     9,        true,   10.0,     3.5,         IO_NETWORK},
		{"D11", 36  * 1024, 8.0,   5.0,     4,        true,   3.0,      1.0,         IO_KEYBOARD},
		{"D12", 88  * 1024, 16.0,  6.0,     5,        false,  0.0,      0.0,         IO_NONE},
		{"D13", 52  * 1024, 11.0,  6.0,     1,        true,   4.0,      2.0,         IO_DISK},
		{"D14", 112 * 1024, 20.0,  7.0,     7,        true,   7.0,      2.8,         IO_PRINTER},
		{"D15", 44  * 1024, 7.0,   7.0,     3,        false,  0.0,      0.0,         IO_NONE},
		{"D16", 76  * 1024, 13.0,  8.0,     6,        true,   5.5,      1.4,         IO_MOUSE},
		{"D17", 60  * 1024, 10.0,  8.0,     2,        true,   3.5,      1.9,         IO_NETWORK},
		{"D18", 104 * 1024, 19.0,  9.0,     8,        false,  0.0,      0.0,         IO_NONE},
		{"D19", 30  * 1024, 6.0,   9.0,     0,        true,   2.0,      0.9,         IO_DISK},
	};

	for (int i = 0; i < 20; i++) {
		struct Pcb *p = malloc(sizeof(*p));

		if (p == NULL) {
			fprintf(stderr, "OOM al crear proceso demo.\n");
			return;
		}

		*p = pcb_defaults();

		snprintf(p->name, sizeof(p->name), "%s", demos[i].name);
		p->pid = s->next_pid++;
		p->state = NEW;
		
		p->mem.required_kb = demos[i].memory_kb;
		
		p->sched.arrival_time = demos[i].arrival;
		p->sched.burst_time = demos[i].burst;
		p->sched.remaining_time = demos[i].burst;
		p->sched.priority = demos[i].priority;
		p->sched.remaining_quantum = s->quantum;
		
		p->io.has_io = demos[i].has_io;
		p->io.start_time = demos[i].io_start;
		if (p->io.has_io) {
			p->io.duration = demos[i].io_duration;
			p->io.remaining_time = demos[i].io_duration;
			p->io.device = demos[i].device;
		}
		
		p->interrupt.periodic_target =
			interrupt_target_for(p->mem.required_kb, p->sched.burst_time);
		p->interrupt.next_cpu_time =
			p->sched.burst_time / (p->interrupt.periodic_target + 1.0);
		
		if (i == 4) {
			p->err.planned = true;
			p->err.planned_type = INT_EXC_DIV_ZERO;
			p->err.trigger_cpu_time = p->sched.burst_time * 0.40;
		}
		
		s->user_process_count++;

		enqueue(&s->created_processes, p);
		
		log_event(s, "PROCESS", "%s(%d) demo creado: memoria=%d MB, burst=%.1f.",
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

	while (assigned < OS_RESERVED_KB / BLOCK_SIZE_KB) {
		blocks[rand() % OS_PROCESS_COUNT]++;
		assigned++;
	}

	for (int i = 0; i < OS_PROCESS_COUNT; i++) {
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

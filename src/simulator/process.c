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

void demo(struct Simulator *s)
{
	
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

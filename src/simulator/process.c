#include "process.h"

#include "dispatcher.h"
#include "interrupt.h"
#include "memory.h"
#include "names.h"
#include "process_table.h"
#include "queue.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MIN_RANDOM_IO_REQUESTS 10

static struct Pcb pcb_defaults(void)
{
	struct Pcb p;

	memset(&p, 0, sizeof(p));

	p.cpu_ctx.stack_pointer = -1;
	p.mem.start = -1;
	p.mem.limit = -1;
	p.mem.text_percent = DEFAULT_TEXT_PERCENT;
	p.mem.data_percent = DEFAULT_DATA_PERCENT;
	p.mem.dynamic_percent = DEFAULT_DYNAMIC_PERCENT;
	p.sched.start_time = -1.0;
	p.sched.finish_time = -1.0;
	p.io.device = IO_NONE;
	p.io.duration = -1.0;
	p.io.remaining_time = -1.0;
	p.err.occurred_at = -1.0;
	p.state = NONE;

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

static double clamp_factor(double value)
{
	if (value < 0.0)
		return 0.0;
	if (value > 1.0)
		return 1.0;
	return value;
}

static double io_duration_for(int mem_kb, double burst)
{
	double memory_factor = clamp_factor((double)mem_kb / (192.0 * 1024.0));
	double burst_factor = clamp_factor(burst / 30.0);
	double process_factor = (memory_factor + burst_factor) / 2.0;
	double duration = 5.0 + process_factor * 10.0 + rand() % 6;

	if (duration > 20.0)
		return 20.0;
	return duration;
}

static enum IoDevice random_io_device(void)
{
	static const enum IoDevice devices[] = {
		IO_KEYBOARD, IO_DISK, IO_PRINTER
	};

	return devices[rand() % (sizeof(devices) / sizeof(devices[0]))];
}

static void configure_process_io(struct Pcb *p, int mem_kb, double burst)
{
	p->io.has_io = true;
	p->io.started = false;
	p->io.completed = false;
	p->io.start_time = burst * (0.15 + (rand() % 66) / 100.0);
	p->io.duration = io_duration_for(mem_kb, burst);
	p->io.remaining_time = p->io.duration;
	p->io.device = random_io_device();
}

struct Pcb create_user_pcb(struct Simulator *s, const char *name, int mem_kb,
			   double burst, double arrival, int priority,
			   int text_percent, int data_percent,
			   int dynamic_percent)
{
	struct Pcb p = pcb_defaults();

	snprintf(p.name, sizeof(p.name), "%s", name);
	p.pid = s->next_pid++;

	p.mem.required_kb = mem_kb;
	p.mem.text_percent = text_percent;
	p.mem.data_percent = data_percent;
	p.mem.dynamic_percent = dynamic_percent;
	
	p.sched.arrival_time = arrival;
	p.sched.burst_time = burst;
	p.sched.remaining_time = burst;
	p.sched.priority = priority;
	p.sched.remaining_quantum = s->quantum;

	/* Entrada y Salida */
	if (rand() % 100 < 65)
		configure_process_io(&p, mem_kb, burst);

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

	return p;
}

void create_random_processes(struct Simulator *s)
{
	int io_target = s->random_process_count < MIN_RANDOM_IO_REQUESTS ?
			s->random_process_count : MIN_RANDOM_IO_REQUESTS;
	int io_count = 0;

	for (int i = 0; i < s->random_process_count; i++) {
		struct Pcb pcb;
		struct Pcb *p;
		char name[16];
		int memory = (24 + rand() % 169) * 1024;
		double burst = 4.0 + rand() % 27;
		double arrival = rand() % 13;
		int priority = rand() % 6;
		int remaining_slots = s->random_process_count - i;
		int remaining_io = io_target - io_count;

		snprintf(name, sizeof(name), "P%d", s->next_pid);
		pcb = create_user_pcb(s, name, memory, burst, arrival, priority,
				      DEFAULT_TEXT_PERCENT, DEFAULT_DATA_PERCENT,
				      DEFAULT_DYNAMIC_PERCENT);

		if (!pcb.io.has_io && remaining_io >= remaining_slots)
			configure_process_io(&pcb, memory, burst);
		if (pcb.io.has_io)
			io_count++;

		p = process_table_add(&s->process_table, pcb);

		if (p == NULL) {
			fprintf(stderr, "OOM al crear un proceso aleatorio.\n");
			return;
		}

		s->user_process_count++;
		log_event(s, "PROCESS", "%s(%d) creado: memoria=%d MB, burst=%.1f.",
			  p->name, p->pid, p->mem.required_kb / 1024,
			  p->sched.burst_time);
	}
}

void test(struct Simulator *s)
{
	static const struct {
		const char *name;
		int memory_kb;
		double burst;
		double arrival;
		int priority;
		int text_percent;
		int data_percent;
		int dynamic_percent;
	} tests[] = {
	/*	 Name,  Memory,     Burst, Arrival, Priority, Text, Data, Dynamic */
		{"T00", 32  * 1024, 8.0,   0.0,     2,        30,   30,   40},
		{"T01", 48  * 1024, 12.0,  0.0,     4,        35,   25,   40},
		{"T02", 24  * 1024, 5.0,   1.0,     1,        25,   35,   40},
		{"T03", 96  * 1024, 18.0,  1.0,     5,        40,   30,   30},
		{"T04", 64  * 1024, 10.0,  2.0,     3,        30,   40,   30},
		{"T05", 40  * 1024, 7.0,   2.0,     5,        20,   40,   40},
		{"T06", 128 * 1024, 22.0,  3.0,     5,        45,   25,   30},
		{"T07", 56  * 1024, 9.0,   3.0,     0,        25,   25,   50},
		{"T08", 72  * 1024, 14.0,  4.0,     5,        35,   35,   30},
		{"T09", 28  * 1024, 6.0,   4.0,     2,        20,   30,   50},
		{"T10", 144 * 1024, 25.0,  5.0,     5,        50,   20,   30},
		{"T11", 36  * 1024, 8.0,   5.0,     4,        30,   25,   45},
		{"T12", 88  * 1024, 16.0,  6.0,     5,        40,   20,   40},
		{"T13", 52  * 1024, 11.0,  6.0,     1,        25,   45,   30},
		{"T14", 112 * 1024, 20.0,  7.0,     5,        45,   30,   25},
		{"T15", 44  * 1024, 7.0,   7.0,     3,        20,   35,   45},
		{"T16", 76  * 1024, 13.0,  8.0,     5,        30,   20,   50},
		{"T17", 60  * 1024, 10.0,  8.0,     2,        35,   30,   35},
		{"T18", 104 * 1024, 19.0,  9.0,     5,        40,   35,   25},
		{"T19", 30  * 1024, 6.0,   9.0,     0,        25,   30,   45},
	};

	for (int i = 0; i < 20; i++) {
		struct Pcb pcb;
		struct Pcb *p;

		pcb = create_user_pcb(s, tests[i].name, tests[i].memory_kb,
				      tests[i].burst, tests[i].arrival,
				      tests[i].priority, tests[i].text_percent,
				      tests[i].data_percent,
				      tests[i].dynamic_percent);
		p = process_table_add(&s->process_table, pcb);
		if (p == NULL) {
			fprintf(stderr, "OOM al crear proceso test.\n");
			return;
		}
		s->user_process_count++;
		
		log_event(s, "PROCESS", "%s(%d) test creado: memoria=%d MB, burst=%.1f.",
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
		struct Pcb pcb = pcb_defaults();
		struct Pcb *p;

		snprintf(pcb.name, sizeof(pcb.name), "%s", names[i]);
		pcb.pid = i;
		pcb.state = BLOCKED;
		pcb.is_system = true;
		pcb.mem.required_kb = blocks[i] * BLOCK_SIZE_KB;
		pcb.sched.priority = 0;
		pcb.resident = false;
		p = process_table_add(&s->process_table, pcb);

		if (p == NULL) {
			fprintf(stderr, "OOM al crear procesos del SO.\n");
			exit(EXIT_FAILURE);
		}

		if (!kmalloc(s, p)) {
			fprintf(stderr, "No se pudo reservar memoria para %s.\n", p->name);
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

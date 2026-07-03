#include "simulator.h"

#include "gantt.h"
#include "memory.h"
#include "process.h"
#include "queue.h"

#include <stdlib.h>
#include <string.h>

struct Simulator simulator_init(void)
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
	s.random_process_count = 5;
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

void simulator_free(struct Simulator *s)
{
	int i;

	if (s->running != NULL)
		free(s->running);
	if (s->next_pcb != NULL)
		free(s->next_pcb);
	q_free(&s->system_q);
	q_free(&s->created_processes);
	q_free(&s->job_q);
	q_free(&s->ready_q);
	for (i = 0; i < IO_DEVICE_COUNT; i++)
		q_free(&s->device_q[i]);
	q_free(&s->nonresident_q);
	q_free(&s->finished_q);
	memory_free_all(&s->memory_list);
	gantt_free(&s->gantt);
}

#include "scheduler.h"

#include "memory.h"
#include "names.h"
#include "process.h"
#include "queue.h"

#include <stdio.h>

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

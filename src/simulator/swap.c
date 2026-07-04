#include "swap.h"

#include "memory.h"
#include "names.h"
#include "queue.h"

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
		s->swap_out_count++;
		log_event(s, "SWAPPER", "%s(%d) descargado; libera %d MB.",
			  candidate->name, candidate->pid,
			  candidate->mem.required_kb / 1024);
		swap_in_ready_processes(s);
		waiting = waiting_for_memory(s);
	}
}

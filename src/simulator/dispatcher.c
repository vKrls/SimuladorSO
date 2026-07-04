#include "dispatcher.h"

#include "memory.h"
#include "names.h"
#include "queue.h"
#include "scheduler.h"

void dispatch_save_ctx(struct Simulator *s)
{
	if (s->running == NULL)
		return;
	s->running->cpu_ctx = s->cpu_ctx;
	memory_save_cpu_offsets(s->running);
	log_event(s, "DISPATCHER", "Contexto guardado de %s(%d): PC=%d.",
		  s->running->name, s->running->pid,
		  s->running->cpu_ctx.program_counter);
}

void dispatch_restore_ctx(struct Simulator *s, struct Pcb *p)
{
	if (p == NULL)
		return;
	memory_restore_cpu_addresses(p);
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

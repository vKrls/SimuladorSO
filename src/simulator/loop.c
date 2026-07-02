#include "loop.h"

#include "cpu.h"
#include "dispatcher.h"
#include "gantt.h"
#include "io.h"
#include "names.h"
#include "protocol.h"
#include "queue.h"
#include "scheduler.h"
#include "swap.h"

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

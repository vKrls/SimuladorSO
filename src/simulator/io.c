#include "io.h"

#include "dispatcher.h"
#include "interrupt.h"
#include "names.h"
#include "process.h"
#include "queue.h"

#include <stdio.h>
#include <stdlib.h>

static bool keyboard_cancelled(void)
{
	return rand() % 100 < 20;
}

static void cancel_by_keyboard(struct Simulator *s, struct Pcb *p,
			       enum IoDevice device)
{
	p->io.remaining_time = 0.0;
	p->io.completed = true;
	record_interrupt(s, p, INT_IO_COMPLETE, device, true);
	dequeue_pcb(&s->device_q[device], p);
	p->err.has_error = true;
	p->err.fatal = true;
	p->err.occurred_at = s->current_time;
	snprintf(p->err.error_code, sizeof(p->err.error_code),
		 "ERR_KEYBOARD_CANCEL");
	snprintf(p->err.error_desc, sizeof(p->err.error_desc),
		 "Cancelación por señal de teclado");
	log_event(s, "IO", "%s(%d): teclado=CANCEL.", p->name, p->pid);
	finish_process(s, p, true);
}

void running_to_blocked(struct Simulator *s)
{
	struct Pcb *p = s->running;

	if (p == NULL || p->io.device < 0 || p->io.device >= IO_DEVICE_COUNT)
		return;
	record_interrupt(s, p, INT_IO_REQUEST, p->io.device, false);
	dispatch_save_ctx(s);
	p->io.started = true;
	p->io.remaining_time = p->io.duration;
	log_event(s, "IO",
		  "%s(%d): request device=%s duration=%.1f mem=%dMB burst=%.1f.",
		  p->name, p->pid, io_device_name(p->io.device), p->io.duration,
		  p->mem.required_kb / 1024, p->sched.burst_time);
	set_process_state(s, p, BLOCKED, "solicitud de entrada/salida");
	enqueue(&s->device_q[p->io.device], p);
	s->running = NULL;
	s->cpu_busy = false;
}

void blocked_to_ready(struct Simulator *s, struct Pcb *p, enum IoDevice device)
{
	p->io.remaining_time = 0.0;
	p->io.completed = true;
	record_interrupt(s, p, INT_IO_COMPLETE, device, false);
	dequeue_pcb(&s->device_q[device], p);
	if (device == IO_KEYBOARD)
		log_event(s, "IO", "%s(%d): teclado=CONTINUE.",
			  p->name, p->pid);
	set_process_state(s, p, READY, "entrada/salida completada");
	enqueue(&s->ready_q, p);
}

void tick_device_queues(struct Simulator *s, double delta)
{
	int i;

	for (i = 0; i < IO_DEVICE_COUNT; i++) {
		struct Pcb *p;
		if (q_empty(&s->device_q[i]))
			continue;
		p = s->device_q[i].head->pcb;
		p->io.remaining_time -= delta;
		if (p->io.remaining_time <= TIME_EPSILON && !p->resident) {
			p->io.remaining_time = 0.0;
			p->io.completed = true;
			if (p->io.device == IO_KEYBOARD && keyboard_cancelled()) {
				cancel_by_keyboard(s, p, p->io.device);
				continue;
			}
			record_interrupt(s, p, INT_IO_COMPLETE, p->io.device, false);
			dequeue_pcb(&s->device_q[i], p);
			if (p->io.device == IO_KEYBOARD)
				log_event(s, "IO", "%s(%d): teclado=CONTINUE.",
					  p->name, p->pid);
			set_process_state(s, p, READY,
					  "I/O terminó fuera de memoria");
			enqueue(&s->nonresident_q, p);
		} else if (p->io.remaining_time <= TIME_EPSILON) {
			if (p->io.device == IO_KEYBOARD && keyboard_cancelled()) {
				cancel_by_keyboard(s, p, (enum IoDevice)i);
				continue;
			}
			blocked_to_ready(s, p, (enum IoDevice)i);
		}
	}
}

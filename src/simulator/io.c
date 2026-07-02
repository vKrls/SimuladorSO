#include "io.h"

#include "dispatcher.h"
#include "interrupt.h"
#include "names.h"
#include "queue.h"

void running_to_blocked(struct Simulator *s)
{
	struct Pcb *p = s->running;

	if (p == NULL || p->io.device < 0 || p->io.device >= IO_DEVICE_COUNT)
		return;
	record_interrupt(s, p, INT_SW_SYSCALL, p->io.device, false);
	dispatch_save_ctx(s);
	p->io.started = true;
	p->io.remaining_time = p->io.duration;
	set_process_state(s, p, BLOCKED, "solicitud de entrada/salida");
	enqueue(&s->device_q[p->io.device], p);
	s->running = NULL;
	s->cpu_busy = false;
}

void blocked_to_ready(struct Simulator *s, struct Pcb *p, enum IoDevice device)
{
	p->io.remaining_time = 0.0;
	p->io.completed = true;
	record_interrupt(s, p, INT_HW_IO, device, false);
	dequeue_pcb(&s->device_q[device], p);
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
			record_interrupt(s, p, INT_HW_IO, p->io.device, false);
			dequeue_pcb(&s->device_q[i], p);
			set_process_state(s, p, READY,
					  "I/O terminó fuera de memoria");
			enqueue(&s->nonresident_q, p);
		} else if (p->io.remaining_time <= TIME_EPSILON) {
			blocked_to_ready(s, p, (enum IoDevice)i);
		}
	}
}

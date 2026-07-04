#include "cpu.h"

#include "dispatcher.h"
#include "interrupt.h"
#include "io.h"
#include "names.h"
#include "process.h"
#include "queue.h"

#include <stdlib.h>

void tick_running_process(struct Simulator *s, double delta)
{
	struct Pcb *p = s->running;
	double executed;

	if (p == NULL)
		return;

	p->sched.remaining_time -= delta;
	p->sched.cpu_time += delta;
	s->cpu_process_time += delta;
	s->cpu_ctx.program_counter++;
	s->cpu_ctx.pc_offset++;

	if (s->alg_sched == ROUND)
		p->sched.remaining_quantum -= delta;

	executed = p->sched.cpu_time;
	while (p->interrupt.periodic_done < p->interrupt.periodic_target &&
	       executed + TIME_EPSILON >= p->interrupt.next_cpu_time) {
		enum IntType type = rand() % 100 < 70
			? INT_HW_TIMER : INT_SW_SYSCALL;
		record_interrupt(s, p, type, IO_NONE, false);
		p->interrupt.periodic_done++;
		p->interrupt.next_cpu_time =
			p->sched.burst_time * (p->interrupt.periodic_done + 1.0) /
			(p->interrupt.periodic_target + 1.0);
	}

	if (p->err.planned && !p->err.has_error &&
	    executed + TIME_EPSILON >= p->err.trigger_cpu_time) {
		if (p->err.planned_type == INT_EXC_DIV_ZERO)
			fail_running_process(s, INT_EXC_DIV_ZERO, "ERR_DIV_ZERO",
					     "División entre cero simulada");
		else
			fail_running_process(s, INT_EXC_MEM, "ERR_MEM_ACCESS",
					     "Acceso inválido a memoria simulada");
		return;
	}

	if (p->sched.remaining_time <= TIME_EPSILON) {
		terminate_running_process(s);
		return;
	}

	if (p->io.has_io && !p->io.started &&
	    executed + TIME_EPSILON >= p->io.start_time) {
		running_to_blocked(s);
		return;
	}
	
	if (s->alg_sched == ROUND &&
	    p->sched.remaining_quantum <= TIME_EPSILON) {
		record_interrupt(s, p, INT_HW_TIMER, IO_NONE, false);
		dispatch_save_ctx(s);
		p->sched.remaining_quantum = s->quantum;
		set_process_state(s, p, READY, "quantum agotado");
		enqueue(&s->ready_q, p);
		s->running = NULL;
		s->cpu_busy = false;
	}
}

#include "interrupt.h"

#include "names.h"

#include <string.h>

void record_interrupt(struct Simulator *s, struct Pcb *p, enum IntType type,
		      enum IoDevice device, bool fatal)
{
	struct InterruptData *data = &p->interrupt;
	struct InterruptEvent *event;

	if (data->history_count == MAX_INTERRUPT_HISTORY) {
		memmove(&data->history[0], &data->history[1],
			sizeof(data->history[0]) * (MAX_INTERRUPT_HISTORY - 1));
		data->history_count--;
	}
	event = &data->history[data->history_count++];
	event->type = type;
	event->device = device;
	event->time = s->current_time;
	event->fatal = fatal;
	data->total++;
	if (type >= 0 && type < INT_TYPE_COUNT)
		data->by_type[type]++;
	s->interrupt_count++;
	log_event(s, "INTERRUPT", "%s(%d): %s%s%s.",
		  p->name, p->pid, interrupt_type_name(type),
		  device == IO_NONE ? "" : " dispositivo=",
		  device == IO_NONE ? "" : io_device_name(device));
}

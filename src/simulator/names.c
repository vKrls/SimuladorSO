#include "names.h"

#include <stdarg.h>
#include <stdio.h>

const char *process_state_name(enum ProcessState state)
{
	switch (state) {
	case NONE: return "NONE";
	case NEW: return "NEW";
	case READY: return "READY";
	case RUNNING: return "RUNNING";
	case BLOCKED: return "BLOCKED";
	case TERMINATED: return "TERMINATED";
	default: return "UNKNOWN";
	}
}

const char *scheduler_algorithm_name(enum AlgorithmSched algorithm)
{
	switch (algorithm) {
	case FCFS: return "FCFS";
	case NP_SJF: return "SJF no expropiativo";
	case P_SJF: return "SJF expropiativo";
	case ROUND: return "Round Robin";
	case NP_PRIOR: return "Prioridad no expropiativa";
	case P_PRIOR: return "Prioridad expropiativa";
	default: return "Desconocido";
	}
}

const char *memory_algorithm_name(enum AlgorithmMem algorithm)
{
	switch (algorithm) {
	case FIRST: return "First Fit";
	case BEST: return "Best Fit";
	case WORST: return "Worst Fit";
	default: return "Desconocido";
	}
}

const char *io_device_name(enum IoDevice device)
{
	switch (device) {
	case IO_KEYBOARD: return "KEYBOARD";
	case IO_MOUSE: return "MOUSE";
	case IO_DISK: return "DISK";
	case IO_PRINTER: return "PRINTER";
	case IO_NETWORK: return "NETWORK";
	default: return "NONE";
	}
}

const char *interrupt_type_name(enum IntType type)
{
	switch (type) {
	case INT_HW_IO: return "HW_IO";
	case INT_HW_TIMER: return "HW_TIMER";
	case INT_SW_SYSCALL: return "SW_SYSCALL";
	case INT_IO_REQUEST: return "IO_REQUEST";
	case INT_IO_COMPLETE: return "IO_COMPLETE";
	case INT_EXC_DIV_ZERO: return "EXC_DIV_ZERO";
	case INT_EXC_MEM: return "EXC_MEMORY";
	default: return "UNKNOWN";
	}
}

const char *gantt_type_name(enum GanttType type)
{
	switch (type) {
	case GANTT_PROCESS: return "PROCESS";
	case GANTT_IDLE: return "IDLE";
	case GANTT_CONTEXT_SWITCH: return "CONTEXT_SWITCH";
	default: return "UNKNOWN";
	}
}

const char *segment_type_name(enum SegmentType type)
{
	switch (type) {
	case SEG_TEXT: return "TEXT";
	case SEG_DATA: return "DATA";
	case SEG_BSS: return "BSS";
	case SEG_HEAP: return "HEAP";
	case SEG_STACK: return "STACK";
	default: return "UNKNOWN";
	}
}

void log_event(struct Simulator *s, const char *category, const char *format, ...)
{
	va_list args;
	double current_time = s == NULL ? 0.0 : s->current_time;

	printf("LOG [t=%.3f] [%s] ", current_time, category);
	va_start(args, format);
	vprintf(format, args);
	va_end(args);
	putchar('\n');
	fflush(stdout);
}

void set_process_state(struct Simulator *s, struct Pcb *p,
		       enum ProcessState state, const char *reason)
{
	enum ProcessState previous;

	if (p == NULL)
		return;
	previous = p->state;
	p->state = state;
	if (previous != state)
		log_event(s, "STATE", "%s(%d): %s -> %s (%s).",
			  p->name, p->pid, process_state_name(previous),
			  process_state_name(state), reason);
}

#ifndef SIMULATOR_NAMES_H
#define SIMULATOR_NAMES_H

#include "simulator.h"

const char *process_state_name(enum ProcessState state);
const char *scheduler_algorithm_name(enum AlgorithmSched algorithm);
const char *memory_algorithm_name(enum AlgorithmMem algorithm);
const char *io_device_name(enum IoDevice device);
const char *interrupt_type_name(enum IntType type);
const char *gantt_type_name(enum GanttType type);
void log_event(struct Simulator *s, const char *category, const char *format, ...);
void set_process_state(struct Simulator *s, struct Pcb *p,
		       enum ProcessState state, const char *reason);

#endif

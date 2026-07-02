#ifndef SIMULATOR_INTERRUPT_H
#define SIMULATOR_INTERRUPT_H

#include "simulator.h"

void record_interrupt(struct Simulator *s, struct Pcb *p, enum IntType type,
		      enum IoDevice device, bool fatal);

#endif

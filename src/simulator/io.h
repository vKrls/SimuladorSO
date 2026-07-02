#ifndef SIMULATOR_IO_H
#define SIMULATOR_IO_H

#include "simulator.h"

void running_to_blocked(struct Simulator *s);
void blocked_to_ready(struct Simulator *s, struct Pcb *p, enum IoDevice device);
void tick_device_queues(struct Simulator *s, double delta);

#endif

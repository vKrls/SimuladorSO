#ifndef SIMULATOR_DISPATCHER_H
#define SIMULATOR_DISPATCHER_H

#include "simulator.h"

void dispatch_save_ctx(struct Simulator *s);
void dispatch_restore_ctx(struct Simulator *s, struct Pcb *p);
void dispatch(struct Simulator *s);
void begin_context_switch(struct Simulator *s);

#endif

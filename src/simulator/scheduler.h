#ifndef SIMULATOR_SCHEDULER_H
#define SIMULATOR_SCHEDULER_H

#include "simulator.h"

void process_arrival(struct Simulator *s);
void job_scheduler(struct Simulator *s);
void scheduler(struct Simulator *s);
struct Pcb *alg_fcfs(struct Simulator *s);
struct Pcb *alg_sjf(struct Simulator *s);
struct Pcb *alg_priority(struct Simulator *s);
bool should_preempt(struct Simulator *s);

#endif

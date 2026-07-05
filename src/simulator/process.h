#ifndef SIMULATOR_PROCESS_H
#define SIMULATOR_PROCESS_H

#include "simulator.h"

struct Pcb create_user_pcb(struct Simulator *s, const char *name, int mem_kb,
			   double burst, double arrival, int priority,
			   int text_percent, int data_percent,
			   int dynamic_percent);
void create_random_processes(struct Simulator *s);
void test(struct Simulator *s);
void create_system_processes(struct Simulator *s);
void finish_process(struct Simulator *s, struct Pcb *p, bool failed);
void terminate_running_process(struct Simulator *s);
void fail_running_process(struct Simulator *s, enum IntType type,
			  const char *code, const char *description);

#endif

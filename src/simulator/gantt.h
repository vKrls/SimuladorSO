#ifndef SIMULATOR_GANTT_H
#define SIMULATOR_GANTT_H

#include "simulator.h"

struct GanttList gantt_init(void);
void update_gantt_interval(struct Simulator *s, enum GanttType type,
			   struct Pcb *p, double delta);
void gantt_free(struct GanttList *g);

#endif

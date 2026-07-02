#ifndef SIMULATOR_LOOP_H
#define SIMULATOR_LOOP_H

#include "simulator.h"

void tick_background(struct Simulator *s, double delta);
bool simulation_finished(struct Simulator *s);
void main_loop(struct Simulator *s);

#endif

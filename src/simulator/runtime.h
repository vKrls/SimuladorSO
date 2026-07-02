#ifndef SIMULATOR_RUNTIME_H
#define SIMULATOR_RUNTIME_H

#include "simulator.h"

struct Simulator simulator_init(void);
void simulator_free(struct Simulator *s);

#endif

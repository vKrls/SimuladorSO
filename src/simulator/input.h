#ifndef SIMULATOR_INPUT_H
#define SIMULATOR_INPUT_H

#include "simulator.h"

void process_stdin(struct Simulator *s, char *line);
bool stdin_has_data(void);

#endif

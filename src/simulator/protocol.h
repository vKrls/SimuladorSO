#ifndef SIMULATOR_PROTOCOL_H
#define SIMULATOR_PROTOCOL_H

#include "simulator.h"

void send_json_string(const char *text);
void send_data(struct Simulator *s, bool force);

#endif

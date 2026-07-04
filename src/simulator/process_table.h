#ifndef SIMULATOR_PROCESS_TABLE_H
#define SIMULATOR_PROCESS_TABLE_H

#include "simulator.h"

void process_table_init(struct ProcessTable *table);
struct Pcb *process_table_add(struct ProcessTable *table, struct Pcb pcb);
bool process_table_has_pending_arrivals(const struct ProcessTable *table);
void process_table_free(struct ProcessTable *table);

#endif

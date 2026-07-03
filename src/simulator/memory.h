#ifndef SIMULATOR_MEMORY_H
#define SIMULATOR_MEMORY_H

#include "simulator.h"

struct MemoryBlockList mem_init(void);
void update_max_mem(struct MemoryBlockList *m);
bool kmalloc(struct Simulator *s, struct Pcb *p);
void kfree(struct MemoryBlockList *m, struct Pcb *p);
void kmerge(struct MemoryBlockList *m);
bool memory_can_fit(struct Simulator *s, struct Pcb *p);
void memory_clear_segments(struct MemoryData *mem);
void memory_layout_segments(struct Pcb *p);
bool memory_grow_heap(struct Pcb *p, int blocks);
bool memory_grow_stack(struct Pcb *p, int blocks);
void memory_free_all(struct MemoryBlockList *m);

#endif

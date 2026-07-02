#ifndef SIMULATOR_QUEUE_H
#define SIMULATOR_QUEUE_H

#include "simulator.h"

struct Queue init_queue(void);
bool q_empty(const struct Queue *q);
void enqueue(struct Queue *q, struct Pcb *p);
struct Pcb *dequeue_head(struct Queue *q);
void dequeue_pcb(struct Queue *q, struct Pcb *p);
void q_free(struct Queue *q);
void accumulate_queue_time(struct Queue *q, double delta, int kind);

#endif

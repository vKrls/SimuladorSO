#include "queue.h"

#include <stdlib.h>

struct Queue init_queue(void)
{
	struct Queue q = {0};
	return q;
}

bool q_empty(const struct Queue *q)
{
	return q->cont == 0;
}

void enqueue(struct Queue *q, struct Pcb *p)
{
	struct Node *node = malloc(sizeof(*node));

	if (node == NULL)
		return;
	node->pcb = p;
	node->next = NULL;
	if (q->tail == NULL) {
		q->head = node;
		q->tail = node;
	} else {
		q->tail->next = node;
		q->tail = node;
	}
	q->cont++;
}

struct Pcb *dequeue_head(struct Queue *q)
{
	struct Node *node;
	struct Pcb *p;

	if (q_empty(q))
		return NULL;
	node = q->head;
	p = node->pcb;
	q->head = node->next;
	if (q->head == NULL)
		q->tail = NULL;
	free(node);
	q->cont--;
	return p;
}

void dequeue_pcb(struct Queue *q, struct Pcb *p)
{
	struct Node *node = q->head;
	struct Node *previous = NULL;

	while (node != NULL) {
		if (node->pcb == p) {
			if (previous == NULL)
				q->head = node->next;
			else
				previous->next = node->next;
			if (q->tail == node)
				q->tail = previous;
			free(node);
			q->cont--;
			return;
		}
		previous = node;
		node = node->next;
	}
}

void q_free(struct Queue *q)
{
	while (!q_empty(q))
		(void)dequeue_head(q);
}

void accumulate_queue_time(struct Queue *q, double delta, int kind)
{
	struct Node *node;

	for (node = q->head; node != NULL; node = node->next) {
		if (kind == 0)
			node->pcb->sched.ready_time += delta;
		else if (kind == 1)
			node->pcb->sched.blocked_time += delta;
		else
			node->pcb->sched.nonresident_time += delta;
	}
}

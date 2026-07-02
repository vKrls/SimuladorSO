#include "gantt.h"

#include "names.h"

#include <stdio.h>
#include <stdlib.h>

struct GanttList gantt_init(void)
{
	struct GanttList gantt = {0};
	return gantt;
}

void update_gantt_interval(struct Simulator *s, enum GanttType type,
			   struct Pcb *p, double delta)
{
	struct GanttNode *tail = s->gantt.tail;
	int owner = -1;
	const char *name = "IDLE";

	if (type == GANTT_PROCESS && p != NULL) {
		owner = p->pid;
		name = p->name;
	} else if (type == GANTT_CONTEXT_SWITCH) {
		owner = -2;
		name = "CS";
	}
	if (tail != NULL && tail->type == type && tail->owner == owner) {
		tail->limit += delta;
		return;
	}
	tail = malloc(sizeof(*tail));
	if (tail == NULL)
		return;
	tail->start = s->current_time;
	tail->limit = s->current_time + delta;
	tail->type = type;
	tail->owner = owner;
	snprintf(tail->name, sizeof(tail->name), "%s", name);
	tail->next = NULL;
	if (s->gantt.tail == NULL) {
		s->gantt.head = tail;
		s->gantt.tail = tail;
	} else {
		s->gantt.tail->next = tail;
		s->gantt.tail = tail;
	}
	s->gantt.cont++;
}

void gantt_free(struct GanttList *g)
{
	struct GanttNode *node = g->head;
	while (node != NULL) {
		struct GanttNode *next = node->next;
		free(node);
		node = next;
	}
}

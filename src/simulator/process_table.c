#include "process_table.h"

#include <stdlib.h>

void process_table_init(struct ProcessTable *table)
{
	table->count = 0;
	table->head = NULL;
	table->tail = NULL;
}

struct Pcb *process_table_add(struct ProcessTable *table, struct Pcb pcb)
{
	struct ProcessTableNode *node = malloc(sizeof(*node));

	if (node == NULL)
		return NULL;
	node->pcb = pcb;
	node->next = NULL;
	if (table->tail == NULL) {
		table->head = node;
		table->tail = node;
	} else {
		table->tail->next = node;
		table->tail = node;
	}
	table->count++;
	return &node->pcb;
}

bool process_table_has_pending_arrivals(const struct ProcessTable *table)
{
	const struct ProcessTableNode *node;

	for (node = table->head; node != NULL; node = node->next)
		if (!node->pcb.is_system && node->pcb.state == NONE)
			return true;
	return false;
}

void process_table_free(struct ProcessTable *table)
{
	struct ProcessTableNode *node = table->head;

	while (node != NULL) {
		struct ProcessTableNode *next = node->next;
		free(node);
		node = next;
	}
	process_table_init(table);
}

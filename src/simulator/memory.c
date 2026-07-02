#include "memory.h"

#include <stdlib.h>

struct MemoryBlockList mem_init(void)
{
	struct MemoryBlockList m = {0};
	struct MemoryBlock *os = malloc(sizeof(*os));
	struct MemoryBlock *free_block = malloc(sizeof(*free_block));
	int os_blocks = OS_RESERVED_KB / BLOCK_SIZE_KB;

	if (os == NULL || free_block == NULL) {
		free(os);
		free(free_block);
		return m;
	}

	os->start = 0;
	os->limit = os_blocks;
	os->length = os_blocks;
	os->owner = NULL;
	os->next = free_block;

	free_block->start = os_blocks;
	free_block->limit = TOTAL_BLOCKS;
	free_block->length = TOTAL_BLOCKS - os_blocks;
	free_block->owner = NULL;
	free_block->next = NULL;

	m.cont = 2;
	m.free = free_block->length;
	m.head = os;
	m.tail = free_block;
	m.max = free_block;
	return m;
}

void update_max_mem(struct MemoryBlockList *m)
{
	struct MemoryBlock *block = m->head;
	struct MemoryBlock *max = NULL;

	while (block != NULL) {
		if (block->owner == NULL &&
		    (max == NULL || block->length > max->length))
			max = block;
		block = block->next;
	}
	m->max = max;
}

static bool allocate_block(struct MemoryBlockList *m, struct MemoryBlock *free_block,
			   struct MemoryBlock *previous, struct Pcb *p,
			   int blocks_needed)
{
	struct MemoryBlock *allocated = malloc(sizeof(*allocated));

	if (allocated == NULL)
		return false;
	allocated->start = free_block->start;
	allocated->limit = free_block->start + blocks_needed;
	allocated->length = blocks_needed;
	allocated->owner = p;

	if (blocks_needed == free_block->length) {
		allocated->next = free_block->next;
		if (previous == NULL)
			m->head = allocated;
		else
			previous->next = allocated;
		if (m->tail == free_block)
			m->tail = allocated;
		free(free_block);
	} else {
		allocated->next = free_block;
		free_block->start = allocated->limit;
		free_block->length = free_block->limit - free_block->start;
		if (previous == NULL)
			m->head = allocated;
		else
			previous->next = allocated;
		m->cont++;
	}

	p->mem.block = allocated;
	p->mem.start = allocated->start;
	p->mem.limit = allocated->limit;
	p->mem.assigned_blocks = blocks_needed;
	p->mem.waste_kb = blocks_needed * BLOCK_SIZE_KB - p->mem.required_kb;
	p->resident = true;
	m->free -= blocks_needed;
	update_max_mem(m);
	return true;
}

bool memory_can_fit(struct Simulator *s, struct Pcb *p)
{
	int needed = (p->mem.required_kb + BLOCK_SIZE_KB - 1) / BLOCK_SIZE_KB;
	return needed > 0 && s->memory_list.max != NULL &&
	       needed <= s->memory_list.max->length;
}

bool kmalloc(struct Simulator *s, struct Pcb *p)
{
	struct MemoryBlockList *m = &s->memory_list;
	struct MemoryBlock *block = m->head;
	struct MemoryBlock *previous = NULL;
	struct MemoryBlock *selected = NULL;
	struct MemoryBlock *selected_previous = NULL;
	int needed = (p->mem.required_kb + BLOCK_SIZE_KB - 1) / BLOCK_SIZE_KB;

	if (needed <= 0 || needed > TOTAL_BLOCKS || !memory_can_fit(s, p))
		return false;

	while (block != NULL) {
		if (block->owner == NULL && block->length >= needed) {
			if (s->alg_memory == FIRST) {
				selected = block;
				selected_previous = previous;
				break;
			}
			if (selected == NULL ||
			    (s->alg_memory == BEST && block->length < selected->length) ||
			    (s->alg_memory == WORST && block->length > selected->length)) {
				selected = block;
				selected_previous = previous;
			}
		}
		previous = block;
		block = block->next;
	}
	return selected != NULL &&
	       allocate_block(m, selected, selected_previous, p, needed);
}

void kmerge(struct MemoryBlockList *m)
{
	struct MemoryBlock *block = m->head;

	while (block != NULL && block->next != NULL) {
		if (block->owner == NULL && block->next->owner == NULL) {
			struct MemoryBlock *discard = block->next;
			block->limit = discard->limit;
			block->length += discard->length;
			block->next = discard->next;
			if (m->tail == discard)
				m->tail = block;
			free(discard);
			m->cont--;
		} else {
			block = block->next;
		}
	}
	update_max_mem(m);
}

void kfree(struct MemoryBlockList *m, struct Pcb *p)
{
	struct MemoryBlock *block = p->mem.block;

	if (block == NULL || block->owner != p)
		return;
	block->owner = NULL;
	m->free += block->length;
	p->mem.block = NULL;
	p->mem.start = -1;
	p->mem.limit = -1;
	p->mem.assigned_blocks = 0;
	p->mem.waste_kb = 0;
	p->resident = false;
	kmerge(m);
}

void memory_free_all(struct MemoryBlockList *m)
{
	struct MemoryBlock *block = m->head;
	while (block != NULL) {
		struct MemoryBlock *next = block->next;
		free(block);
		block = next;
	}
}

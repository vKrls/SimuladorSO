#include "memory.h"

#include <stdlib.h>

static int max_int(int a, int b)
{
	return a > b ? a : b;
}

static int min_int(int a, int b)
{
	return a < b ? a : b;
}

static void set_segment(struct ProcessSegment *segment, enum SegmentType type,
			int start_block, int assigned_blocks, int required_kb)
{
	int capacity_kb = assigned_blocks * BLOCK_SIZE_KB;

	segment->type = type;
	segment->assigned_blocks = assigned_blocks;
	segment->required_kb = min_int(required_kb, capacity_kb);
	segment->waste_kb = capacity_kb - segment->required_kb;
	segment->start_block = start_block;
	segment->limit_block = start_block + assigned_blocks;
}

static int segment_required_kb(struct MemoryData *mem, int percent,
			       int assigned_blocks)
{
	if (assigned_blocks <= 0)
		return 0;
	return max_int(1, mem->required_kb * percent / 100);
}

static struct ProcessSegment *find_segment(struct MemoryData *mem,
					   enum SegmentType type)
{
	int i;

	for (i = 0; i < mem->segment_count; i++)
		if (mem->segments[i].type == type)
			return &mem->segments[i];
	return NULL;
}

struct MemoryBlockList mem_init(void)
{
	struct MemoryBlockList m = {0};
	struct MemoryBlock *free_block = malloc(sizeof(*free_block));

	if (free_block == NULL)
		return m;

	free_block->start = 0;
	free_block->limit = TOTAL_BLOCKS;
	free_block->length = TOTAL_BLOCKS;
	free_block->owner = NULL;
	free_block->next = NULL;

	m.cont = 1;
	m.free = free_block->length;
	m.head = free_block;
	m.tail = free_block;
	m.max = free_block;
	return m;
}

void memory_clear_segments(struct MemoryData *mem)
{
	int i;

	if (mem == NULL)
		return;
	for (i = 0; i < PROCESS_SEGMENT_COUNT; i++) {
		mem->segments[i].type = (enum SegmentType)i;
		mem->segments[i].required_kb = 0;
		mem->segments[i].assigned_blocks = 0;
		mem->segments[i].waste_kb = 0;
		mem->segments[i].start_block = -1;
		mem->segments[i].limit_block = -1;
	}
	mem->segment_count = 0;
}

void memory_layout_segments(struct Pcb *p)
{
	struct MemoryData *mem;
	int blocks[PROCESS_SEGMENT_COUNT] = {0};
	int required[PROCESS_SEGMENT_COUNT] = {0};
	int cursor;
	int total;
	int stack_start;

	if (p == NULL)
		return;
	mem = &p->mem;
	memory_clear_segments(mem);
	if (mem->block == NULL || mem->assigned_blocks <= 0)
		return;

	total = mem->assigned_blocks;
	if (total < PROCESS_SEGMENT_COUNT) {
		int i;
		for (i = 0; i < total; i++)
			blocks[i] = 1;
	} else {
		blocks[SEG_TEXT] = max_int(1, total * 30 / 100);
		blocks[SEG_DATA] = max_int(1, total * 20 / 100);
		blocks[SEG_BSS] = max_int(1, total * 10 / 100);
		blocks[SEG_HEAP] = max_int(1, total * 10 / 100);
		blocks[SEG_STACK] = max_int(1, total * 10 / 100);
	}
	required[SEG_TEXT] = segment_required_kb(mem, 30, blocks[SEG_TEXT]);
	required[SEG_DATA] = segment_required_kb(mem, 20, blocks[SEG_DATA]);
	required[SEG_BSS] = segment_required_kb(mem, 10, blocks[SEG_BSS]);
	required[SEG_HEAP] = segment_required_kb(mem, 10, blocks[SEG_HEAP]);
	required[SEG_STACK] = segment_required_kb(mem, 10, blocks[SEG_STACK]);

	cursor = mem->start;
	set_segment(&mem->segments[SEG_TEXT], SEG_TEXT, cursor,
		    blocks[SEG_TEXT], required[SEG_TEXT]);
	cursor = mem->segments[SEG_TEXT].limit_block;
	set_segment(&mem->segments[SEG_DATA], SEG_DATA, cursor,
		    blocks[SEG_DATA], required[SEG_DATA]);
	cursor = mem->segments[SEG_DATA].limit_block;
	set_segment(&mem->segments[SEG_BSS], SEG_BSS, cursor,
		    blocks[SEG_BSS], required[SEG_BSS]);
	cursor = mem->segments[SEG_BSS].limit_block;
	set_segment(&mem->segments[SEG_HEAP], SEG_HEAP, cursor,
		    blocks[SEG_HEAP], required[SEG_HEAP]);

	stack_start = mem->limit - blocks[SEG_STACK];
	if (stack_start < mem->segments[SEG_HEAP].limit_block)
		stack_start = mem->segments[SEG_HEAP].limit_block;
	set_segment(&mem->segments[SEG_STACK], SEG_STACK,
		    stack_start, mem->limit - stack_start, required[SEG_STACK]);

	mem->segment_count = PROCESS_SEGMENT_COUNT;
	p->cpu_ctx.stack_pointer = mem->segments[SEG_STACK].limit_block;
}

bool memory_grow_heap(struct Pcb *p, int blocks)
{
	struct ProcessSegment *heap;
	struct ProcessSegment *stack;

	if (p == NULL || blocks <= 0 || p->mem.segment_count == 0)
		return false;
	heap = find_segment(&p->mem, SEG_HEAP);
	stack = find_segment(&p->mem, SEG_STACK);
	if (heap == NULL || stack == NULL ||
	    heap->limit_block + blocks > stack->start_block)
		return false;
	heap->limit_block += blocks;
	heap->assigned_blocks += blocks;
	heap->required_kb += blocks * BLOCK_SIZE_KB;
	heap->waste_kb = heap->assigned_blocks * BLOCK_SIZE_KB -
			 heap->required_kb;
	return true;
}

bool memory_grow_stack(struct Pcb *p, int blocks)
{
	struct ProcessSegment *heap;
	struct ProcessSegment *stack;

	if (p == NULL || blocks <= 0 || p->mem.segment_count == 0)
		return false;
	heap = find_segment(&p->mem, SEG_HEAP);
	stack = find_segment(&p->mem, SEG_STACK);
	if (heap == NULL || stack == NULL ||
	    stack->start_block - blocks < heap->limit_block)
		return false;
	stack->start_block -= blocks;
	stack->assigned_blocks += blocks;
	stack->required_kb += blocks * BLOCK_SIZE_KB;
	stack->waste_kb = stack->assigned_blocks * BLOCK_SIZE_KB -
			  stack->required_kb;
	p->cpu_ctx.stack_pointer = stack->start_block;
	return true;
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
	memory_layout_segments(p);
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
	memory_clear_segments(&p->mem);
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

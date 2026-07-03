#include "protocol.h"

#include "gantt.h"
#include "names.h"
#include "queue.h"

#include <stdio.h>
#include <time.h>

static int64_t monotonic_ms(void)
{
	struct timespec now;

	clock_gettime(CLOCK_MONOTONIC, &now);
	return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

void send_json_string(const char *text)
{
	const unsigned char *c = (const unsigned char *)text;
	putchar('"');
	while (*c != '\0') {
		switch (*c) {
		case '"': fputs("\\\"", stdout); break;
		case '\\': fputs("\\\\", stdout); break;
		case '\n': fputs("\\n", stdout); break;
		case '\r': fputs("\\r", stdout); break;
		case '\t': fputs("\\t", stdout); break;
		default:
			if (*c < 0x20)
				printf("\\u%04x", *c);
			else
				putchar(*c);
		}
		c++;
	}
	putchar('"');
}

static void send_interrupts(struct Pcb *p)
{
	int i;

	printf("\"interrupts\":{\"planned\":%d,\"periodic_completed\":%d,"
	       "\"total\":%d,\"by_type\":{",
	       p->interrupt.periodic_target, p->interrupt.periodic_done,
	       p->interrupt.total);
	for (i = 0; i < INT_TYPE_COUNT; i++) {
		if (i > 0)
			putchar(',');
		send_json_string(interrupt_type_name((enum IntType)i));
		printf(":%d", p->interrupt.by_type[i]);
	}
	printf("},\"history\":[");
	for (i = 0; i < p->interrupt.history_count; i++) {
		struct InterruptEvent *event = &p->interrupt.history[i];
		if (i > 0)
			putchar(',');
		printf("{\"type\":");
		send_json_string(interrupt_type_name(event->type));
		printf(",\"time\":%.3f,\"device\":", event->time);
		send_json_string(io_device_name(event->device));
		printf(",\"fatal\":%s}", event->fatal ? "true" : "false");
	}
	printf("]}");
}

static void send_process_segments(struct Pcb *p)
{
	int i;

	putchar('[');
	for (i = 0; i < p->mem.segment_count; i++) {
		struct ProcessSegment *segment = &p->mem.segments[i];
		if (i > 0)
			putchar(',');
		printf("{\"type\":");
		send_json_string(segment_type_name(segment->type));
		printf(",\"required_kb\":%d,\"assigned_blocks\":%d,"
		       "\"waste_kb\":%d,\"start_block\":%d,\"limit_block\":%d}",
		       segment->required_kb, segment->assigned_blocks,
		       segment->waste_kb, segment->start_block,
		       segment->limit_block);
	}
	putchar(']');
}

static void send_pcb(struct Simulator *s, struct Pcb *p)
{
	struct CpuContext cpu = p->cpu_ctx;

	if (s != NULL && p == s->running)
		cpu = s->cpu_ctx;

	printf("{\"pid\":%d,\"name\":", p->pid);
	send_json_string(p->name);
	printf(",\"state\":");
	send_json_string(process_state_name(p->state));
	printf(",\"is_system\":%s,\"resident\":%s,\"swap_count\":%d,"
	       "\"last_swap_out\":%.3f,\"last_swap_in\":%.3f,"
	       "\"cpu\":{\"program_counter\":%d,\"stack_pointer\":%d},"
	       "\"scheduler\":{\"arrival_time\":%.3f,\"burst_time\":%.3f,"
	       "\"remaining_time\":%.3f,\"start_time\":%.3f,\"finish_time\":%.3f,"
	       "\"turnaround_time\":%.3f,\"response_time\":%.3f,\"ready_time\":%.3f,"
	       "\"blocked_time\":%.3f,\"nonresident_time\":%.3f,"
	       "\"cpu_time\":%.3f,\"priority\":%d,\"remaining_quantum\":%.3f,"
	       "\"context_switches\":%d},"
	       "\"memory\":{\"required_kb\":%d,\"assigned_blocks\":%d,"
	       "\"waste_kb\":%d,\"start_block\":%d,\"limit_block\":%d,"
	       "\"block_address\":\"%p\",\"segments\":",
	       p->is_system ? "true" : "false", p->resident ? "true" : "false",
	       p->swap_count, p->last_swap_out, p->last_swap_in,
	       cpu.program_counter, cpu.stack_pointer,
	       p->sched.arrival_time, p->sched.burst_time,
	       p->sched.remaining_time, p->sched.start_time,
	       p->sched.finish_time, p->sched.turnaround_time, p->sched.response_time,
	       p->sched.ready_time, p->sched.blocked_time,
	       p->sched.nonresident_time, p->sched.cpu_time,
	       p->sched.priority, p->sched.remaining_quantum,
	       p->sched.context_switches, p->mem.required_kb,
	       p->mem.assigned_blocks, p->mem.waste_kb,
	       p->mem.start, p->mem.limit, (void *)p->mem.block);
	send_process_segments(p);
	printf("},\"io\":{\"has_io\":%s,\"started\":%s,\"completed\":%s,"
	       "\"start_time\":%.3f,\"duration\":%.3f,\"remaining_time\":%.3f,"
	       "\"device\":",
	       p->io.has_io ? "true" : "false",
	       p->io.started ? "true" : "false",
	       p->io.completed ? "true" : "false",
	       p->io.start_time, p->io.duration, p->io.remaining_time);
	send_json_string(io_device_name(p->io.device));
	printf("},");
	send_interrupts(p);
	printf(",\"error\":{\"planned\":%s,\"has_error\":%s,\"fatal\":%s,"
	       "\"occurred_at\":%.3f,\"code\":",
	       p->err.planned ? "true" : "false",
	       p->err.has_error ? "true" : "false",
	       p->err.fatal ? "true" : "false", p->err.occurred_at);
	send_json_string(p->err.error_code);
	printf(",\"description\":");
	send_json_string(p->err.error_desc);
	printf("}}");
}

static void send_queue_processes(struct Queue *q, bool *first)
{
	struct Node *node;
	for (node = q->head; node != NULL; node = node->next) {
		if (!*first)
			putchar(',');
		send_pcb(NULL, node->pcb);
		*first = false;
	}
}

static void send_all_processes(struct Simulator *s)
{
	bool first = true;
	int i;

	putchar('[');
	send_queue_processes(&s->system_q, &first);
	send_queue_processes(&s->created_processes, &first);
	send_queue_processes(&s->job_q, &first);
	send_queue_processes(&s->ready_q, &first);
	for (i = 0; i < IO_DEVICE_COUNT; i++)
		send_queue_processes(&s->device_q[i], &first);
	send_queue_processes(&s->nonresident_q, &first);
	send_queue_processes(&s->finished_q, &first);
	if (s->running != NULL) {
		if (!first)
			putchar(',');
		send_pcb(s, s->running);
		first = false;
	}
	if (s->next_pcb != NULL) {
		if (!first)
			putchar(',');
		send_pcb(NULL, s->next_pcb);
	}
	putchar(']');
}

static void send_pid_queue(struct Queue *q)
{
	struct Node *node;
	bool first = true;

	putchar('[');
	for (node = q->head; node != NULL; node = node->next) {
		if (!first)
			putchar(',');
		printf("%d", node->pcb->pid);
		first = false;
	}
	putchar(']');
}

static void send_queues(struct Simulator *s)
{
	int i;

	printf("\"queues\":{\"created\":");
	send_pid_queue(&s->created_processes);
	printf(",\"job\":");
	send_pid_queue(&s->job_q);
	printf(",\"ready\":");
	send_pid_queue(&s->ready_q);
	printf(",\"nonresident\":");
	send_pid_queue(&s->nonresident_q);
	printf(",\"finished\":");
	send_pid_queue(&s->finished_q);
	printf(",\"devices\":{");
	for (i = 0; i < IO_DEVICE_COUNT; i++) {
		if (i > 0)
			putchar(',');
		send_json_string(io_device_name((enum IoDevice)i));
		putchar(':');
		send_pid_queue(&s->device_q[i]);
	}
	printf("}}");
}

static void send_memory(struct Simulator *s)
{
	struct MemoryBlock *block;
	bool first = true;

	printf("\"memory\":{\"total_kb\":%d,\"block_size_kb\":%d,"
	       "\"free_kb\":%d,\"os_reserved_kb\":%d,\"blocks\":[",
	       TOTAL_MEMORY_KB, BLOCK_SIZE_KB,
	       s->memory_list.free * BLOCK_SIZE_KB, OS_RESERVED_KB);
	for (block = s->memory_list.head; block != NULL; block = block->next) {
		if (!first)
			putchar(',');
		printf("{\"start_block\":%d,\"limit_block\":%d,"
		       "\"length_blocks\":%d,\"owner_pid\":",
		       block->start, block->limit, block->length);
		if (block->owner == NULL)
			printf("null,\"owner_name\":\"Libre\",\"is_system\":false}");
		else {
			printf("%d,\"owner_name\":", block->owner->pid);
			send_json_string(block->owner->name);
			printf(",\"is_system\":%s}",
			       block->owner->is_system ? "true" : "false");
		}
		first = false;
	}
	printf("]}");
}

static void send_gantt(struct Simulator *s)
{
	struct GanttNode *node;
	bool first = true;

	printf("\"gantt\":{\"current_time\":%.3f,\"segments\":[", s->current_time);
	for (node = s->gantt.head; node != NULL; node = node->next) {
		if (!first)
			putchar(',');
		printf("{\"pid\":%d,\"name\":", node->owner);
		send_json_string(node->name);
		printf(",\"kind\":");
		send_json_string(gantt_type_name(node->type));
		printf(",\"start\":%.3f,\"limit\":%.3f,\"duration\":%.3f}",
		       node->start, node->limit, node->limit - node->start);
		first = false;
	}
	printf("]}");
}

static void send_stats(struct Simulator *s)
{
	struct Node *node;
	double ready = 0.0;
	double turnaround = 0.0;
	double response = 0.0;
	int measured = 0;

	for (node = s->finished_q.head; node != NULL; node = node->next) {
		struct Pcb *p = node->pcb;
		ready += p->sched.ready_time;
		turnaround += p->sched.turnaround_time;
		response += p->sched.response_time;
		measured++;
	}
	printf("\"stats\":{\"avg_ready_time\":%.3f,\"avg_turnaround\":%.3f,"
	       "\"avg_response\":%.3f,\"throughput\":%.6f,\"cpu_util\":%.3f,"
	       "\"total_time\":%.3f,\"completed\":%d,\"errors\":%d,"
	       "\"interrupts\":%d,\"swap_outs\":%d,\"swap_ins\":%d,"
	       "\"context_switches\":%d,\"context_switch_time\":%.3f}",
	       measured == 0 ? 0.0 : ready / measured,
	       measured == 0 ? 0.0 : turnaround / measured,
	       measured == 0 ? 0.0 : response / measured,
	       s->current_time <= 0.0 ? 0.0 :
		       s->completed_count / s->current_time,
	       s->current_time <= 0.0 ? 0.0 :
		       s->cpu_process_time / s->current_time * 100.0,
	       s->current_time, s->completed_count, s->error_count,
	       s->interrupt_count, s->swap_out_count, s->swap_in_count,
	       s->context_switch_count, s->context_switch_time);
}

void send_data(struct Simulator *s, bool force)
{
	int64_t now = monotonic_ms();

	if (!force && s->last_snapshot_ms > 0 &&
	    now - s->last_snapshot_ms < SNAPSHOT_INTERVAL_MS)
		return;
	s->last_snapshot_ms = now;
	s->snapshot_sequence++;

	printf("SIM_DATA {\"type\":\"state\",\"sequence\":%llu,"
	       "\"current_time\":%.3f,\"simulator_state\":%d,"
	       "\"cpu_busy\":%s,\"running_pid\":",
	       (unsigned long long)s->snapshot_sequence, s->current_time,
	       s->state, s->cpu_busy ? "true" : "false");
	if (s->running == NULL)
		printf("null");
	else
		printf("%d", s->running->pid);
	printf(",\"dispatching_pid\":");
	if (s->next_pcb == NULL)
		printf("null");
	else
		printf("%d", s->next_pcb->pid);
	printf(",\"config\":{\"scheduler_algorithm\":%d,\"scheduler_name\":",
	       s->alg_sched);
	send_json_string(scheduler_algorithm_name(s->alg_sched));
	printf(",\"memory_algorithm\":%d,\"memory_name\":", s->alg_memory);
	send_json_string(memory_algorithm_name(s->alg_memory));
	printf(",\"quantum\":%.3f,\"switch_cost\":%.3f,"
	       "\"snapshot_interval_ms\":%d},\"processes\":",
	       s->quantum, s->switch_cost, SNAPSHOT_INTERVAL_MS);
	send_all_processes(s);
	putchar(',');
	send_queues(s);
	putchar(',');
	send_memory(s);
	putchar(',');
	send_gantt(s);
	putchar(',');
	send_stats(s);
	printf("}\n");
	fflush(stdout);
}

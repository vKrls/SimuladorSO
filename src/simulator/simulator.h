#ifndef SIMULATOR_H
#define SIMULATOR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define TICK 0.1
#define TICK_US 100000
#define TIME_EPSILON 1e-9
#define SNAPSHOT_INTERVAL_MS 100

#define TOTAL_MEMORY_KB (1024 * 1024)
#define BLOCK_SIZE_KB 4
#define TOTAL_BLOCKS (TOTAL_MEMORY_KB / BLOCK_SIZE_KB)
#define OS_RESERVED_KB (128 * 1024)
#define USER_MEMORY_KB (TOTAL_MEMORY_KB - OS_RESERVED_KB)

#define RESERVED_PID_COUNT 100
#define OS_PROCESS_COUNT 5
#define RANDOM_PROCESS_COUNT 5
#define IO_DEVICE_COUNT 5
#define MAX_INTERRUPT_HISTORY 32
#define ERR_CODE_MAX 24
#define ERR_DESC_MAX 96

enum SimulatorState {
	SIM_RUN = 0,
	SIM_PAUSE = 1,
	SIM_STOP = 2,
};

enum AlgorithmSched {
	FCFS = 0,
	NP_SJF = 1,
	P_SJF = 2,
	ROUND = 3,
	NP_PRIOR = 4,
	P_PRIOR = 5,
};

enum AlgorithmMem {
	FIRST = 0,
	BEST = 1,
	WORST = 2,
};

enum ProcessState {
	NEW = 0,
	READY = 1,
	RUNNING = 2,
	BLOCKED = 3,
	TERMINATED = 4,
};

enum IoDevice {
	IO_NONE = -1,
	IO_KEYBOARD = 0,
	IO_MOUSE = 1,
	IO_DISK = 2,
	IO_PRINTER = 3,
	IO_NETWORK = 4,
};

enum IntType {
	INT_HW_IO = 0,
	INT_HW_TIMER = 1,
	INT_SW_SYSCALL = 2,
	INT_EXC_DIV_ZERO = 3,
	INT_EXC_MEM = 4,
	INT_TYPE_COUNT = 5,
};

enum GanttType {
	GANTT_PROCESS = 0,
	GANTT_IDLE = 1,
	GANTT_CONTEXT_SWITCH = 2,
};

struct Pcb;
struct MemoryBlock;

struct CpuContext {
	int program_counter;
	int stack_pointer;
};

struct SchedulerData {
	double arrival_time;
	double burst_time;
	double remaining_time;
	double start_time;
	double finish_time;
	double turnaround_time;
	double response_time;
	double ready_time;
	double blocked_time;
	double nonresident_time;
	double cpu_time;
	int priority;
	double remaining_quantum;
	int context_switches;
};

struct MemoryData {
	int required_kb;
	int assigned_blocks;
	int waste_kb;
	int start;
	int limit;
	struct MemoryBlock *block;
};

struct IoData {
	bool has_io;
	bool started;
	bool completed;
	double start_time;
	double duration;
	double remaining_time;
	enum IoDevice device;
};

struct InterruptEvent {
	enum IntType type;
	enum IoDevice device;
	double time;
	bool fatal;
};

struct InterruptData {
	int periodic_target;
	int periodic_done;
	double next_cpu_time;
	int total;
	int by_type[INT_TYPE_COUNT];
	int history_count;
	struct InterruptEvent history[MAX_INTERRUPT_HISTORY];
};

struct ErrorData {
	bool planned;
	bool has_error;
	bool fatal;
	enum IntType planned_type;
	double trigger_cpu_time;
	double occurred_at;
	char error_code[ERR_CODE_MAX];
	char error_desc[ERR_DESC_MAX];
};

struct Pcb {
	char name[16];
	int pid;
	enum ProcessState state;
	bool is_system;
	bool resident;
	int swap_count;
	double last_swap_out;
	double last_swap_in;
	struct CpuContext cpu_ctx;
	struct MemoryData mem;
	struct SchedulerData sched;
	struct IoData io;
	struct ErrorData err;
	struct InterruptData interrupt;
};

struct Node {
	struct Pcb *pcb;
	struct Node *next;
};

struct Queue {
	int cont;
	struct Node *head;
	struct Node *tail;
};

struct MemoryBlock {
	int start;
	int limit;
	int length;
	struct Pcb *owner;
	struct MemoryBlock *next;
};

struct MemoryBlockList {
	int cont;
	int free;
	struct MemoryBlock *head;
	struct MemoryBlock *tail;
	struct MemoryBlock *max;
};

struct GanttNode {
	double start;
	double limit;
	enum GanttType type;
	int owner;
	char name[16];
	struct GanttNode *next;
};

struct GanttList {
	int cont;
	struct GanttNode *head;
	struct GanttNode *tail;
};

struct Simulator {
	enum SimulatorState state;
	double current_time;
	int sim_speed;
	int next_pid;

	enum AlgorithmSched alg_sched;
	enum AlgorithmMem alg_memory;
	double quantum;
	double switch_cost;
	double switch_remaining;

	struct Queue system_q;
	struct Queue created_processes;
	struct Queue job_q;
	struct Queue ready_q;
	struct Queue device_q[IO_DEVICE_COUNT];
	struct Queue nonresident_q;
	struct Queue finished_q;

	struct Pcb *running;
	struct Pcb *next_pcb;
	struct CpuContext cpu_ctx;
	bool cpu_busy;

	struct MemoryBlockList memory_list;
	struct GanttList gantt;

	int user_process_count;
	int completed_count;
	int error_count;
	int interrupt_count;
	int swap_out_count;
	int swap_in_count;
	int context_switch_count;
	double cpu_process_time;
	double idle_time;
	double context_switch_time;

	uint64_t snapshot_sequence;
	int64_t last_snapshot_ms;
};

const char *process_state_name(enum ProcessState state);
const char *scheduler_algorithm_name(enum AlgorithmSched algorithm);
const char *memory_algorithm_name(enum AlgorithmMem algorithm);
const char *io_device_name(enum IoDevice device);
const char *interrupt_type_name(enum IntType type);
const char *gantt_type_name(enum GanttType type);
void log_event(struct Simulator *s, const char *category, const char *format, ...);
void set_process_state(struct Simulator *s, struct Pcb *p,
		       enum ProcessState state, const char *reason);

struct Queue init_queue(void);
bool q_empty(const struct Queue *q);
void enqueue(struct Queue *q, struct Pcb *p);
struct Pcb *dequeue_head(struct Queue *q);
void dequeue_pcb(struct Queue *q, struct Pcb *p);
void q_free(struct Queue *q);
void accumulate_queue_time(struct Queue *q, double delta, int kind);

struct MemoryBlockList mem_init(void);
void update_max_mem(struct MemoryBlockList *m);
bool kmalloc(struct Simulator *s, struct Pcb *p);
void kfree(struct MemoryBlockList *m, struct Pcb *p);
void kmerge(struct MemoryBlockList *m);
bool memory_can_fit(struct Simulator *s, struct Pcb *p);
void memory_free_all(struct MemoryBlockList *m);

struct Pcb create_user_pcb(struct Simulator *s, const char *name, int mem_kb,
			   double burst, double arrival, int priority);
void create_random_processes(struct Simulator *s);
void demo(struct Simulator *s);
void create_system_processes(struct Simulator *s);
void finish_process(struct Simulator *s, struct Pcb *p, bool failed);
void terminate_running_process(struct Simulator *s);
void fail_running_process(struct Simulator *s, enum IntType type,
			  const char *code, const char *description);

void record_interrupt(struct Simulator *s, struct Pcb *p, enum IntType type,
		      enum IoDevice device, bool fatal);
void running_to_blocked(struct Simulator *s);
void blocked_to_ready(struct Simulator *s, struct Pcb *p, enum IoDevice device);
void tick_device_queues(struct Simulator *s, double delta);
void mid_term_scheduler(struct Simulator *s);

void process_arrival(struct Simulator *s);
void job_scheduler(struct Simulator *s);
void scheduler(struct Simulator *s);
struct Pcb *alg_fcfs(struct Simulator *s);
struct Pcb *alg_sjf(struct Simulator *s);
struct Pcb *alg_priority(struct Simulator *s);
bool should_preempt(struct Simulator *s);
void dispatch_save_ctx(struct Simulator *s);
void dispatch_restore_ctx(struct Simulator *s, struct Pcb *p);
void dispatch(struct Simulator *s);
void begin_context_switch(struct Simulator *s);
void tick_running_process(struct Simulator *s, double delta);

struct GanttList gantt_init(void);
void update_gantt_interval(struct Simulator *s, enum GanttType type,
			   struct Pcb *p, double delta);
void gantt_free(struct GanttList *g);
void tick_background(struct Simulator *s, double delta);
bool simulation_finished(struct Simulator *s);
void main_loop(struct Simulator *s);

void send_json_string(const char *text);
void send_data(struct Simulator *s, bool force);
void process_stdin(struct Simulator *s, char *line);
bool stdin_has_data(void);

struct Simulator simulator_init(void);
void simulator_free(struct Simulator *s);

#endif

#ifndef SIMULATOR_H
#define SIMULATOR_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define TICK 0.1
#define TICK_US 100000
#define TIME_EPSILON 1e-9
#define SNAPSHOT_INTERVAL_MS 100

#define TOTAL_MEMORY_KB (1024 * 1024)				/* 1GB de memoria en total */
#define BLOCK_SIZE_KB 4
#define TOTAL_BLOCKS (TOTAL_MEMORY_KB / BLOCK_SIZE_KB)
#define OS_RESERVED_KB (128 * 1024)				/* 128MB reservado para procesos SO */
#define USER_MEMORY_KB (TOTAL_MEMORY_KB - OS_RESERVED_KB)

#define RESERVED_PID_COUNT 100
#define OS_PROCESS_COUNT 5
#define IO_DEVICE_COUNT 5
#define MAX_INTERRUPT_HISTORY 32
#define ERR_CODE_MAX 24
#define ERR_DESC_MAX 96
#define PROCESS_SEGMENT_COUNT 5

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

enum SegmentType {
	SEG_TEXT = 0,
	SEG_DATA = 1,
	SEG_BSS = 2,
	SEG_HEAP = 3,
	SEG_STACK = 4,
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
	int program_counter;		/* Heap */
	int stack_pointer;		/* Stack */
};

struct SchedulerData {
	double arrival_time;		/* El proceso llega al sistema */
	double burst_time;		/* Constante */
	double remaining_time;		/* Burst restante */
	double start_time;		/* Primera ejecucion */
	double finish_time;		/* Termina el proceso */
	double turnaround_time;		/* Desde arrival hasta finished */
	double response_time;		/* Desde arrival hasta start */
	double ready_time;		/* Tiempo en listos */
	double blocked_time;		/* Tiempo bloqueado */
	double nonresident_time;	/* Tiempo fuera de memoria BLOCKED / READY */
	double cpu_time;		/* Tiempo ejecutandose */
	int priority;
	double remaining_quantum;
	int context_switches;		/* Cada vez que entra a los registros */
};

struct ProcessSegment {
	enum SegmentType type;
	int required_kb;
	int assigned_blocks;
	int waste_kb;
	int start_block;
	int limit_block;
};

struct MemoryData {
	int required_kb;
	int assigned_blocks;
	int waste_kb;
	int start;
	int limit;
	struct MemoryBlock *block;

	struct ProcessSegment segments[PROCESS_SEGMENT_COUNT];
	int segment_count;
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
	int random_process_count;

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

struct Simulator simulator_init(void);
void simulator_free(struct Simulator *s);

#endif

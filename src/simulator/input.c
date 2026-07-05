#include "input.h"

#include "names.h"
#include "process.h"
#include "process_table.h"
#include "protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool valid_config(int sched, int memory, double quantum, double cost,
			 int speed)
{
	if (sched < FCFS || sched > P_PRIOR || memory < FIRST || memory > WORST)
		return false;
	if (quantum < 0.0 || cost < 0.0 || cost > 100.0)
		return false;
	if (sched == ROUND && quantum <= 0.0)
		return false;
	if (speed < 1 || speed > 100)
		return false;
	return true;
}

static bool valid_sched(int sched)
{
	return sched >= FCFS && sched <= P_PRIOR;
}

static bool valid_memory(int memory)
{
	return memory >= FIRST && memory <= WORST;
}

static bool valid_quantum(double quantum)
{
	return quantum > 0.0;
}

static bool valid_switch_cost(double cost)
{
	return cost >= 0.0 && cost <= 100.0;
}

static bool valid_speed(int speed)
{
	return speed >= 1 && speed <= 100;
}

static bool valid_segment_percentages(int text, int data, int dynamic)
{
	return text > 0 && data > 0 && dynamic > 0 &&
	       text + data + dynamic == 100;
}

static void apply_config(struct Simulator *s, int sched, int memory,
			 double quantum, double cost, int speed)
{
	s->alg_sched = (enum AlgorithmSched)sched;
	s->alg_memory = (enum AlgorithmMem)memory;
	s->quantum = quantum;
	s->switch_cost = cost;
	s->sim_speed = speed;
	log_event(s, "CONFIG",
		  "Planificador=%s, memoria=%s, quantum=%.2f, cambio=%.2f, velocidad=%dx.",
		  scheduler_algorithm_name(s->alg_sched),
		  memory_algorithm_name(s->alg_memory),
		  s->quantum, s->switch_cost, s->sim_speed);
	send_data(s, true);
}

static void send_config_state(struct Simulator *s)
{
	log_event(s, "CONFIG",
		  "Planificador=%s, memoria=%s, quantum=%.2f, cambio=%.2f, velocidad=%dx.",
		  scheduler_algorithm_name(s->alg_sched),
		  memory_algorithm_name(s->alg_memory),
		  s->quantum, s->switch_cost, s->sim_speed);
	send_data(s, true);
}

void process_stdin(struct Simulator *s, char *line)
{
	if (strncmp(line, "SET_CONFIG", 10) == 0) {
		int sched;
		int memory;
		double quantum;
		double cost;
		int speed;
		int parsed = sscanf(line, "SET_CONFIG %d %d %lf %lf %d",
				    &sched, &memory, &quantum, &cost, &speed);

		if (parsed != 5 ||
		    !valid_config(sched, memory, quantum, cost, speed)) {
			log_event(s, "ERROR", "SET_CONFIG inválido: %s", line);
			return;
		}

		apply_config(s, sched, memory, quantum, cost, speed);
		return;
	}

	if (strncmp(line, "SET_ALG_SCHED", 13) == 0) {
		int sched;

		if (sscanf(line, "SET_ALG_SCHED %d", &sched) != 1 ||
		    !valid_sched(sched)) {
			log_event(s, "ERROR", "SET_ALG_SCHED inválido: %s", line);
			return;
		}

		if ((enum AlgorithmSched)sched == ROUND &&
		    !valid_quantum(s->quantum)) {
			log_event(s, "ERROR",
				  "SET_ALG_SCHED inválido: Round Robin requiere quantum > 0.");
			return;
		}

		s->alg_sched = (enum AlgorithmSched)sched;
		send_config_state(s);
		return;
	}

	if (strncmp(line, "SET_ALG_MEM", 11) == 0) {
		int memory;

		if (sscanf(line, "SET_ALG_MEM %d", &memory) != 1 ||
		    !valid_memory(memory)) {
			log_event(s, "ERROR", "SET_ALG_MEM inválido: %s", line);
			return;
		}

		s->alg_memory = (enum AlgorithmMem)memory;
		send_config_state(s);
		return;
	}

	if (strncmp(line, "SET_QUANTUM", 11) == 0) {
		double quantum;

		if (sscanf(line, "SET_QUANTUM %lf", &quantum) != 1 ||
		    !valid_quantum(quantum)) {
			log_event(s, "ERROR", "SET_QUANTUM inválido: %s", line);
			return;
		}

		s->quantum = quantum;
		send_config_state(s);
		return;
	}

	if (strncmp(line, "SET_SWITCH_COST", 15) == 0) {
		double cost;

		if (sscanf(line, "SET_SWITCH_COST %lf", &cost) != 1 ||
		    !valid_switch_cost(cost)) {
			log_event(s, "ERROR", "SET_SWITCH_COST inválido: %s", line);
			return;
		}

		s->switch_cost = cost;
		send_config_state(s);
		return;
	}

	if (strncmp(line, "SET_SPEED", 9) == 0) {
		int speed;

		if (sscanf(line, "SET_SPEED %d", &speed) != 1 ||
		    !valid_speed(speed)) {
			log_event(s, "ERROR", "SET_SPEED inválido: %s", line);
			return;
		}

		s->sim_speed = speed;
		send_config_state(s);
		return;
	}

	if (strncmp(line, "SET_SEED", 8) == 0) {
		unsigned int seed;

		if (sscanf(line, "SET_SEED %u", &seed) != 1) {
			log_event(s, "ERROR", "SET_SEED inválido: %s", line);
			return;
		}

		srand(seed);
		log_event(s, "CONFIG", "Semilla aleatoria=%u.", seed);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "ADD", 3) == 0) {
		char name[16];
		int mem_kb;
		double burst;
		double arrival;
		int priority;
		int text_percent = DEFAULT_TEXT_PERCENT;
		int data_percent = DEFAULT_DATA_PERCENT;
		int dynamic_percent = DEFAULT_DYNAMIC_PERCENT;
		struct Pcb pcb;
		struct Pcb *p;
		int parsed = sscanf(line, "ADD %15s %d %lf %lf %d %d %d %d",
				    name, &mem_kb, &burst, &arrival, &priority,
				    &text_percent, &data_percent,
				    &dynamic_percent);

		if ((parsed != 5 && parsed != 8) || mem_kb <= 0 ||
		    burst <= 0.0 || arrival < 0.0 || priority < 0 ||
		    priority > 5 ||
		    !valid_segment_percentages(text_percent, data_percent,
					       dynamic_percent)) {
			log_event(s, "ERROR", "ADD inválido: %s", line);
			return;
		}

		pcb = create_user_pcb(s, name, mem_kb, burst, arrival,
				      priority, text_percent, data_percent,
				      dynamic_percent);
		p = process_table_add(&s->process_table, pcb);

		if (p == NULL) {
			fprintf(stderr, "OOM al crear proceso.\n");
			return;
		}

		s->user_process_count++;
		log_event(s, "PROCESS", "%s(%d) creado.", p->name, p->pid);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "RANDOM", 6) == 0) {
		int count;

		if (sscanf(line, "RANDOM %d", &count) != 1 ||
		    count < 1 || count > 20) {
			log_event(s, "ERROR", "RANDOM inválido: %s", line);
			return;
		}

		s->random_process_count = count;
		create_random_processes(s);
		log_event(s, "SIMULATOR", "%d procesos aleatorios cargados.", count);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "SPEED", 5) == 0) {
		int speed;

		if (sscanf(line, "SPEED %d", &speed) != 1 ||
		    !valid_speed(speed)) {
			log_event(s, "ERROR", "SPEED inválido: %s", line);
			return;
		}

		s->sim_speed = speed;
		log_event(s, "CONFIG", "Velocidad de simulación=%dx.", s->sim_speed);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "RUN", 3) == 0) {
		s->state = SIM_RUN;
		log_event(s, "SIMULATOR", "Simulación iniciada.");
		send_data(s, true);
		return;
	}
	if (strncmp(line, "PAUSE", 5) == 0) {
		s->state = SIM_PAUSE;
		log_event(s, "SIMULATOR", "Simulación pausada.");
		send_data(s, true);
		return;
	}
	if (strncmp(line, "STOP", 4) == 0) {
		s->state = SIM_STOP;
		log_event(s, "SIMULATOR", "Simulación detenida.");
		send_data(s, true);
		return;
	}

	if (strncmp(line, "TEST", 4) == 0) {
		test(s);
		log_event(s, "SIMULATOR", "20 procesos de prueba cargados.");
		send_data(s, true);
		return;
	}

	log_event(s, "ERROR", "Comando desconocido: %s", line);
}

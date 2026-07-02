#include "input.h"

#include "names.h"
#include "process.h"
#include "protocol.h"
#include "queue.h"

#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static bool valid_config(int sched, int memory, double quantum, double cost)
{
	if (sched < FCFS || sched > P_PRIOR || memory < FIRST || memory > WORST)
		return false;
	if (quantum < 0.0 || cost < 0.0 || cost > 100.0)
		return false;
	if (sched == ROUND && quantum <= 0.0)
		return false;
	return true;
}

void process_stdin(struct Simulator *s, char *line)
{
	if (strncmp(line, "CONFIG", 6) == 0) {
		int sched;
		int memory;
		double quantum;
		double cost;
		int parsed = sscanf(line, "CONFIG %d %d %lf %lf",
				    &sched, &memory, &quantum, &cost);
		if (parsed != 4 || !valid_config(sched, memory, quantum, cost)) {
			log_event(s, "ERROR", "CONFIG inválido: %s", line);
			return;
		}
		s->alg_sched = (enum AlgorithmSched)sched;
		s->alg_memory = (enum AlgorithmMem)memory;
		s->quantum = quantum;
		s->switch_cost = cost;
		log_event(s, "CONFIG",
			  "Planificador=%s, memoria=%s, quantum=%.2f, cambio=%.2f.",
			  scheduler_algorithm_name(s->alg_sched),
			  memory_algorithm_name(s->alg_memory),
			  s->quantum, s->switch_cost);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "ADD", 3) == 0) {
		char name[16];
		int mem_kb;
		double burst;
		double arrival;
		int priority;
		struct Pcb *p;
		int parsed = sscanf(line, "ADD %15s %d %lf %lf %d",
				    name, &mem_kb, &burst, &arrival, &priority);
		if (parsed != 5 || mem_kb <= 0 || burst <= 0.0 ||
		    arrival < 0.0 || priority < 0 || priority > 99) {
			log_event(s, "ERROR", "ADD inválido: %s", line);
			return;
		}
		p = malloc(sizeof(*p));
		if (p == NULL) {
			fprintf(stderr, "OOM al crear proceso.\n");
			return;
		}
		*p = create_user_pcb(s, name, mem_kb, burst, arrival, priority);
		enqueue(&s->created_processes, p);
		log_event(s, "PROCESS", "%s(%d) creado.", p->name, p->pid);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "RANDOM", 6) == 0) {
		create_random_processes(s);
		send_data(s, true);
		return;
	}

	if (strncmp(line, "SPEED", 5) == 0) {
		int speed;
		if (sscanf(line, "SPEED %d", &speed) != 1 ||
		    speed < 1 || speed > 100) {
			log_event(s, "ERROR", "SPEED inválido: %s", line);
			return;
		}
		s->sim_speed = speed;
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

	if (strncmp(line, "DEMO", 4) == 0) {
		demo(s);
		log_event(s, "SIMULATOR", "20 procesos de prueba cargados.");
		send_data(s, true);
		return;
	}

	log_event(s, "ERROR", "Comando desconocido: %s", line);
}

bool stdin_has_data(void)
{
	struct pollfd fd = {0};
	fd.fd = STDIN_FILENO;
	fd.events = POLLIN;
	return poll(&fd, 1, 0) > 0 &&
	       (fd.revents & (POLLIN | POLLHUP | POLLERR | POLLNVAL));
}

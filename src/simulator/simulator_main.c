#include "input.h"
#include "loop.h"
#include "protocol.h"
#include "simulator.h"

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

int main(void)
{
	struct Simulator simulator;
	char line[256];

	srand((unsigned int)time(NULL));
	simulator = simulator_init();
	setvbuf(stdin, NULL, _IONBF, 0);
	setvbuf(stdout, NULL, _IOLBF, 0);
	send_data(&simulator, true);

	while (simulator.state != SIM_STOP) {
		usleep((useconds_t)(TICK_US / simulator.sim_speed));
		while (stdin_has_data()) {
			if (fgets(line, sizeof(line), stdin) == NULL) {
				if (simulator.state == SIM_PAUSE)
					simulator.state = SIM_STOP;
				break;
			}
			process_stdin(&simulator, line);
			if (simulator.state == SIM_STOP)
				break;
		}
		if (simulator.state == SIM_RUN)
			main_loop(&simulator);
	}
	simulator_free(&simulator);
	return EXIT_SUCCESS;
}

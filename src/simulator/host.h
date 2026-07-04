#ifndef SIMULATOR_HOST_H
#define SIMULATOR_HOST_H

#include <stdbool.h>
#include <stdint.h>

void sleep_us(unsigned int microseconds);
bool stdin_has_data(void);
int64_t monotonic_ms(void);

#endif

#define _POSIX_C_SOURCE 200809L

#include "host.h"

#ifndef _WIN32

#include <errno.h>
#include <poll.h>
#include <time.h>
#include <unistd.h>

void sleep_us(unsigned int microseconds)
{
	struct timespec delay;

	delay.tv_sec = microseconds / 1000000U;
	delay.tv_nsec = (long)(microseconds % 1000000U) * 1000L;
	while (nanosleep(&delay, &delay) == -1 && errno == EINTR);
}

bool stdin_has_data(void)
{
	struct pollfd fd = {0};

	fd.fd = STDIN_FILENO;
	fd.events = POLLIN;
	return poll(&fd, 1, 0) > 0 &&
	       (fd.revents & (POLLIN | POLLHUP | POLLERR | POLLNVAL));
}

int64_t monotonic_ms(void)
{
	struct timespec now;

	clock_gettime(CLOCK_MONOTONIC, &now);
	return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

#endif

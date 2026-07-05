#include "host.h"

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <conio.h>
#include <windows.h>

#ifndef CREATE_WAITABLE_TIMER_HIGH_RESOLUTION
#define CREATE_WAITABLE_TIMER_HIGH_RESOLUTION 0x00000002
#endif

#define HUNDRED_NS_PER_US 10LL
#define SPIN_TAIL_US 500U

static LARGE_INTEGER performance_frequency(void)
{
	static LARGE_INTEGER frequency;

	if (frequency.QuadPart == 0)
		QueryPerformanceFrequency(&frequency);
	return frequency;
}

static LONGLONG performance_counter(void)
{
	LARGE_INTEGER counter;

	QueryPerformanceCounter(&counter);
	return counter.QuadPart;
}

static LONGLONG microseconds_to_ticks(unsigned int microseconds)
{
	LARGE_INTEGER frequency = performance_frequency();

	return (LONGLONG)microseconds * frequency.QuadPart / 1000000LL;
}

static HANDLE high_resolution_timer(void)
{
	static HANDLE timer;
	static BOOL initialized;

	if (!initialized) {
		timer = CreateWaitableTimerExW(
			NULL, NULL, CREATE_WAITABLE_TIMER_HIGH_RESOLUTION,
			SYNCHRONIZE | TIMER_MODIFY_STATE);
		if (timer == NULL)
			timer = CreateWaitableTimerW(NULL, TRUE, NULL);
		initialized = TRUE;
	}
	return timer;
}

static void wait_with_timer(unsigned int microseconds)
{
	HANDLE timer = high_resolution_timer();
	LARGE_INTEGER due_time;

	if (timer == NULL) {
		Sleep(microseconds / 1000U);
		return;
	}

	due_time.QuadPart = -((LONGLONG)microseconds * HUNDRED_NS_PER_US);
	if (SetWaitableTimer(timer, &due_time, 0, NULL, NULL, FALSE))
		WaitForSingleObject(timer, INFINITE);
}

static void spin_until(LONGLONG target)
{
	while (performance_counter() < target)
		YieldProcessor();
}

void sleep_us(unsigned int microseconds)
{
	LONGLONG target;

	if (microseconds == 0U)
		return;

	target = performance_counter() + microseconds_to_ticks(microseconds);
	if (microseconds > SPIN_TAIL_US)
		wait_with_timer(microseconds - SPIN_TAIL_US);
	spin_until(target);
}

bool stdin_has_data(void)
{
	HANDLE input = GetStdHandle(STD_INPUT_HANDLE);
	DWORD available = 0;
	DWORD type;

	if (input == INVALID_HANDLE_VALUE || input == NULL)
		return false;
	type = GetFileType(input);
	if (type == FILE_TYPE_PIPE) {
		if (!PeekNamedPipe(input, NULL, 0, NULL, &available, NULL))
			return true;
		return available > 0;
	}
	if (type == FILE_TYPE_CHAR)
		return _kbhit() != 0;
	return true;
}

int64_t monotonic_ms(void)
{
	static LARGE_INTEGER frequency;
	static BOOL has_frequency = FALSE;
	LARGE_INTEGER counter;

	if (!has_frequency) {
		frequency = performance_frequency();
		has_frequency = TRUE;
	}
	counter.QuadPart = performance_counter();
	return (int64_t)(counter.QuadPart * 1000 / frequency.QuadPart);
}

#endif

#include "host.h"

#ifdef _WIN32

#define WIN32_LEAN_AND_MEAN
#include <conio.h>
#include <windows.h>

void sleep_us(unsigned int microseconds)
{
	DWORD milliseconds = (microseconds + 999U) / 1000U;

	if (milliseconds == 0U && microseconds > 0U)
		milliseconds = 1U;
	Sleep(milliseconds);
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
		QueryPerformanceFrequency(&frequency);
		has_frequency = TRUE;
	}
	QueryPerformanceCounter(&counter);
	return (int64_t)(counter.QuadPart * 1000 / frequency.QuadPart);
}

#endif

from __future__ import annotations

TICK = 0.1
TICK_US = 50000
TICK_MS = TICK_US // 1000


def timer_interval_ms(speed: int) -> int:
    return max(1, int(round(TICK_MS / max(1, speed))))

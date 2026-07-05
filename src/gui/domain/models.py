from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TOTAL_MEMORY_KB = 1024 * 1024
RESERVED_PID_COUNT = 100
PROCESS_COLORS = [
    "#00d4ff", "#ff6b35", "#7bc67e", "#f7c59f",
    "#c77dff", "#ff4d6d", "#48cae4", "#f4a261",
    "#06d6a0", "#ffd60a", "#e07a5f", "#81b29a",
]

MEMORY_ALGORITHM_NAMES = {
    0: "First Fit",
    1: "Best Fit",
    2: "Worst Fit",
}


@dataclass
class ProcessData:
    name: str
    cpu_burst: float
    memory: int
    arrival_time: float
    priority: int = 0
    quantum: float = 0.0
    text_percent: int = 30
    data_percent: int = 30
    dynamic_percent: int = 40


@dataclass
class UiProcess:
    pid: int
    name: str
    burst_time: float
    memory: int
    arrival_time: float
    priority: int = 0
    quantum: float = 0.0
    text_percent: int = 30
    data_percent: int = 30
    dynamic_percent: int = 40
    state: str = "NONE"
    remaining_time: float | None = None
    assigned_blocks: int = 0
    waste_kb: int = 0
    program_counter: int = 0
    stack_pointer: int = 0
    memory_base: int = 0
    memory_limit: int = 0
    progress: float = 0.0
    start_time: float | None = None
    finish_time: float | None = None
    ready_time: float = 0.0
    turnaround_time: float = 0.0
    response_time: float | None = None
    interrupts: int = 0
    planned_interrupts: int = 0
    interrupt_history: list[dict[str, Any]] = field(default_factory=list)
    interrupt_breakdown: dict[str, int] = field(default_factory=dict)
    is_system: bool = False
    resident: bool = False
    memory_block_address: str = "0x0"
    memory_segments: list[dict[str, Any]] = field(default_factory=list)
    io_device: str = "NONE"
    io_remaining: float = 0.0
    blocked_time: float = 0.0
    nonresident_time: float = 0.0
    cpu_time: float = 0.0
    context_switches: int = 0
    swap_count: int = 0
    error_code: str = ""
    error_description: str = ""
    error_time: float | None = None
    color: str = "#00d4ff"

    def __post_init__(self) -> None:
        if self.remaining_time is None:
            self.remaining_time = self.burst_time

    def to_c_command(self) -> str:
        return (
            f"ADD {self.name} {self.memory} {self.burst_time:.3f} "
            f"{self.arrival_time:.3f} {self.priority} "
            f"{self.text_percent} {self.data_percent} {self.dynamic_percent}"
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "burst_time": self.burst_time,
            "memory_kb": self.memory,
            "arrival_time": self.arrival_time,
            "priority": self.priority,
            "quantum": self.quantum,
            "text_percent": self.text_percent,
            "data_percent": self.data_percent,
            "dynamic_percent": self.dynamic_percent,
            "color": self.color,
        }


@dataclass
class SimulationResult:
    payload: dict[str, Any]
    command_lines: list[str] = field(default_factory=list)
    stdout_lines: list[str] = field(default_factory=list)
    returncode: int | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

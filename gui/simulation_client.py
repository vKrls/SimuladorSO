from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gui.components.visual_widgets import PROCESS_COLORS
from gui.simulation_engine import LocalSimulationEngine


@dataclass
class ProcessData:
    name: str
    cpu_burst: float
    memory: int
    arrival_time: float
    priority: int = 0
    quantum: float = 0.0


@dataclass
class UiProcess:
    pid: int
    name: str
    burst_time: float
    memory: int
    arrival_time: float
    priority: int = 0
    quantum: float = 0.0
    state: str = "NEW"
    remaining_time: float | None = None
    assigned_blocks: int = 0
    waste_kb: int = 0
    program_counter: int = 0
    memory_base: int = 0
    memory_limit: int = 0
    progress: float = 0.0
    start_time: float | None = None
    finish_time: float | None = None
    waiting_time: float = 0.0
    turnaround_time: float = 0.0
    response_time: float | None = None
    interrupts: int = 0
    color: str = "#00d4ff"

    def __post_init__(self) -> None:
        if self.remaining_time is None:
            self.remaining_time = self.burst_time

    def to_payload(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "burst_time": self.burst_time,
            "memory_kb": self.memory,
            "arrival_time": self.arrival_time,
            "priority": self.priority,
            "quantum": self.quantum,
            "color": self.color,
        }


@dataclass
class SimulationResult:
    payload: dict[str, Any]
    stdout: str = ""
    returncode: int | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.returncode == 0


class SimulationClient:
    def __init__(self, engine: LocalSimulationEngine | None = None):
        self.engine = engine or LocalSimulationEngine()
        self._next_pid = 1
        self._processes_by_algorithm: dict[str, list[UiProcess]] = {}

    def processes_for(self, algorithm: str) -> list[UiProcess]:
        return list(self._processes_by_algorithm.get(algorithm, []))

    def add_process(self, algorithm: str, process_data: ProcessData) -> UiProcess:
        pid = self._next_pid
        self._next_pid += 1
        process = UiProcess(
            pid=pid,
            name=process_data.name.strip() or f"P{pid}",
            burst_time=process_data.cpu_burst,
            memory=process_data.memory,
            arrival_time=process_data.arrival_time,
            priority=process_data.priority,
            quantum=process_data.quantum,
            color=self._color_for(pid),
        )
        self._processes_by_algorithm.setdefault(algorithm, []).append(process)
        return process

    def clear_processes(self, algorithm: str) -> None:
        self._processes_by_algorithm[algorithm] = []

    def build_payload(self, algorithm: str) -> dict[str, Any]:
        return {
            "algorithm": algorithm,
            "processes": [process.to_payload() for process in self.processes_for(algorithm)],
        }

    def run(self, algorithm: str, *, apply_events: bool = True) -> SimulationResult:
        payload = self.build_payload(algorithm)
        result = SimulationResult(payload=payload)
        result.stdout, result.events = self.engine.simulate(payload)
        result.returncode = 0
        if apply_events:
            self._apply_events(algorithm, result.events)
        return result

    def apply_result(self, algorithm: str, result: SimulationResult) -> None:
        self._apply_events(algorithm, result.events)

    def stop(self) -> SimulationResult:
        return SimulationResult(payload={}, error="Simulación detenida.")

    def _apply_events(self, algorithm: str, events: list[dict[str, Any]]) -> None:
        processes = {process.pid: process for process in self._processes_by_algorithm.get(algorithm, [])}
        for event in events:
            if event.get("type") != "process_update":
                continue
            process = processes.get(event.get("pid"))
            if process is None:
                continue
            if "state" in event:
                process.state = str(event["state"])
            if "remaining_time" in event:
                process.remaining_time = float(event["remaining_time"])
            if "assigned_blocks" in event:
                process.assigned_blocks = int(event["assigned_blocks"])
            if "waste_kb" in event:
                process.waste_kb = int(event["waste_kb"])
            if "program_counter" in event:
                process.program_counter = int(event["program_counter"])
            if "memory_base" in event:
                process.memory_base = int(event["memory_base"])
            if "memory_limit" in event:
                process.memory_limit = int(event["memory_limit"])
            if "progress" in event:
                process.progress = float(event["progress"])
            if "start_time" in event:
                process.start_time = float(event["start_time"])
            if "finish_time" in event:
                process.finish_time = float(event["finish_time"])
            if "waiting_time" in event:
                process.waiting_time = float(event["waiting_time"])
            if "turnaround_time" in event:
                process.turnaround_time = float(event["turnaround_time"])
            if "response_time" in event:
                process.response_time = float(event["response_time"])
            if "interrupts" in event:
                process.interrupts = int(event["interrupts"])

    def _color_for(self, pid: int) -> str:
        return PROCESS_COLORS[(pid - 1) % len(PROCESS_COLORS)]

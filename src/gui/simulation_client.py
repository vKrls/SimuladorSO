from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import queue
import subprocess
import threading
from typing import Any

from gui.components.visual_widgets import PROCESS_COLORS

RANDOM_PROCESS_COUNT = 5


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

    def to_c_command(self) -> str:
        return (
            f"ADD {self.name} {self.memory} {self.burst_time:.3f} "
            f"{self.arrival_time:.3f} {self.priority}"
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


class SimulationClient:
    def __init__(self, c_executable: Path | None = None):
        project_root = Path(__file__).resolve().parents[2]
        self.c_executable = c_executable or project_root / "build" / "main"
        self._next_pid = 1
        self._processes_by_algorithm: dict[str, list[UiProcess]] = {}
        self._random_requests_by_algorithm: dict[str, int] = {}
        self._random_quantum_by_algorithm: dict[str, float] = {}
        self._process: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str] = queue.Queue()
        self._stderr_queue: queue.Queue[str] = queue.Queue()

    def processes_for(self, algorithm: str) -> list[UiProcess]:
        return list(self._processes_by_algorithm.get(algorithm, []))

    def add_process(self, algorithm: str, process_data: ProcessData) -> UiProcess:
        pid = self._next_pid
        self._next_pid += 1
        process = UiProcess(
            pid=pid,
            name=self._sanitize_name(process_data.name.strip() or f"P{pid}"),
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
        self._random_requests_by_algorithm[algorithm] = 0
        self._random_quantum_by_algorithm.pop(algorithm, None)

    def request_random_processes(self, algorithm: str, quantum: float = 0.0) -> None:
        self._random_requests_by_algorithm[algorithm] = (
            self._random_requests_by_algorithm.get(algorithm, 0) + 1
        )
        if quantum > 0:
            self._random_quantum_by_algorithm[algorithm] = quantum

    def random_process_count_for(self, algorithm: str) -> int:
        requests = self._random_requests_by_algorithm.get(algorithm, 0)
        return requests * RANDOM_PROCESS_COUNT

    def has_processes_for(self, algorithm: str) -> bool:
        return bool(self.processes_for(algorithm) or self.random_process_count_for(algorithm))

    def build_payload(self, algorithm: str) -> dict[str, Any]:
        return {
            "algorithm": algorithm,
            "processes": [process.to_payload() for process in self.processes_for(algorithm)],
            "random_requests": self._random_requests_by_algorithm.get(algorithm, 0),
        }

    def build_c_commands(self, algorithm: str) -> list[str]:
        processes = self.processes_for(algorithm)
        return [
            self.build_config_command(algorithm, processes),
            *[process.to_c_command() for process in processes],
            *["RANDOM"] * self._random_requests_by_algorithm.get(algorithm, 0),
            "RUN",
        ]

    def build_config_command(self, algorithm: str, processes: list[UiProcess]) -> str:
        sched_alg = {
            "fcfs": 0,
            "sjf_nonpreemptive": 1,
            "sjf_preemptive": 2,
            "round_robin": 3,
            "priority_nonpreemptive": 4,
            "priority_preemptive": 5,
        }.get(algorithm, 0)
        memory_alg = 0
        quantum = 0.0
        if algorithm == "round_robin":
            quantum = next(
                (process.quantum for process in processes if process.quantum > 0),
                self._random_quantum_by_algorithm.get(algorithm, 1.0),
            )
        return f"CONFIG {sched_alg} {memory_alg} {quantum:.3f}"

    def run(self, algorithm: str, *, apply_events: bool = True) -> SimulationResult:
        payload = self.build_payload(algorithm)
        command_lines = self.build_c_commands(algorithm)
        result = SimulationResult(payload=payload, command_lines=command_lines)

        if not self.c_executable.exists():
            result.error = f"No existe el ejecutable: {self.c_executable}"
            return result

        try:
            self._ensure_process()
            for line in command_lines:
                self.send_command(line)
        except OSError as exc:
            result.error = str(exc)

        return result

    def send_pause(self) -> SimulationResult:
        return self._send_control("PAUSE")

    def send_run(self) -> SimulationResult:
        return self._send_control("RUN")

    def stop(self) -> SimulationResult:
        result = self._send_control("STOP")
        self.close_process()
        return result

    def read_stdout_lines(self) -> list[str]:
        return self._drain(self._stdout_queue)

    def read_stderr_lines(self) -> list[str]:
        return self._drain(self._stderr_queue)

    def is_process_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def close_process(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1)
        self._process = None

    def _ensure_process(self) -> None:
        if self.is_process_running():
            return

        self._stdout_queue = queue.Queue()
        self._stderr_queue = queue.Queue()
        self._process = subprocess.Popen(
            [str(self.c_executable)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._start_reader(self._process.stdout, self._stdout_queue)
        self._start_reader(self._process.stderr, self._stderr_queue)

    def _start_reader(self, stream, output_queue: queue.Queue[str]) -> None:
        def read_loop() -> None:
            if stream is None:
                return
            for line in stream:
                output_queue.put(line.rstrip("\n"))

        thread = threading.Thread(target=read_loop, daemon=True)
        thread.start()

    def send_command(self, line: str) -> None:
        if not self.is_process_running() or self._process is None or self._process.stdin is None:
            raise OSError("El proceso C no está ejecutándose.")
        self._process.stdin.write(line + "\n")
        self._process.stdin.flush()

    def _send_control(self, command: str) -> SimulationResult:
        result = SimulationResult(payload={}, command_lines=[command])
        try:
            self.send_command(command)
        except OSError as exc:
            result.error = str(exc)
        return result

    def _drain(self, output_queue: queue.Queue[str]) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                lines.append(output_queue.get_nowait())
            except queue.Empty:
                return lines

    def _sanitize_name(self, name: str) -> str:
        cleaned = "".join(ch for ch in name if not ch.isspace())
        return (cleaned or "P")[:15]

    def _color_for(self, pid: int) -> str:
        return PROCESS_COLORS[(pid - 1) % len(PROCESS_COLORS)]

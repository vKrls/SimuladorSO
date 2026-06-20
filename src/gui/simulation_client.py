from __future__ import annotations

from dataclasses import dataclass, field
import json
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
        self.c_executable = c_executable or project_root / "build" / "main.exe"
        self._next_pid = 0
        self._processes_by_algorithm: dict[str, list[UiProcess]] = {}
        self._random_requests_by_algorithm: dict[str, int] = {}
        self._random_quantum_by_algorithm: dict[str, float] = {}
        self._state_by_algorithm: dict[str, dict[str, Any]] = {}
        self._active_algorithm: str | None = None
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
        self._state_by_algorithm.pop(algorithm, None)

    def load_process(
        self,
        algorithm: str,
        process_data: ProcessData,
    ) -> tuple[UiProcess, SimulationResult]:
        process = self.add_process(algorithm, process_data)
        result = self._load_commands(
            algorithm,
            [process.to_c_command()],
        )
        return process, result

    def request_random_processes(
        self,
        algorithm: str,
        quantum: float = 0.0,
    ) -> SimulationResult:
        self._random_requests_by_algorithm[algorithm] = (
            self._random_requests_by_algorithm.get(algorithm, 0) + 1
        )
        if quantum > 0:
            self._random_quantum_by_algorithm[algorithm] = quantum
        return self._load_commands(algorithm, ["RANDOM"])

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
        if self.is_process_running() and self._active_algorithm == algorithm:
            command_lines = ["RUN"]
        else:
            command_lines = self.build_c_commands(algorithm)
        result = SimulationResult(payload=payload, command_lines=command_lines)

        if not self.c_executable.exists():
            result.error = f"No existe el ejecutable: {self.c_executable}"
            return result

        try:
            if self.is_process_running() and self._active_algorithm != algorithm:
                self.close_process()
            self._ensure_process()
            self._active_algorithm = algorithm
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

    def parse_event(self, line: str, algorithm: str) -> dict[str, Any] | None:
        prefix = "SIM_DATA "
        if not line.startswith(prefix):
            return None

        try:
            event = json.loads(line[len(prefix):])
        except json.JSONDecodeError:
            return None

        if event.get("type") == "gantt":
            colors_by_name = {
                process.name: process.color
                for process in self.processes_for(algorithm)
            }
            for segment in event.get("segments", []):
                pid = int(segment.get("pid", 0))
                name = str(segment.get("name", f"P{pid}"))
                segment["color"] = colors_by_name.get(
                    name,
                    PROCESS_COLORS[pid % len(PROCESS_COLORS)],
                )

        return event

    def apply_events(self, algorithm: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        state = self._state_by_algorithm.setdefault(
            algorithm,
            {
                "queues": {},
                "running": None,
                "snapshot": {},
                "memory": {},
                "gantt": {},
            },
        )

        for event in events:
            event_type = event.get("type")
            if event_type == "snapshot":
                state["snapshot"] = event
            elif event_type == "queue":
                self._apply_queue_event(state, event)
            elif event_type == "running":
                state["running"] = event.get("process")
                running = state["running"]
                if running is not None:
                    self._remove_pid_from_queues(state, int(running["pid"]))
            elif event_type == "memory":
                state["memory"] = event
            elif event_type == "gantt":
                state["gantt"] = event

        self._rebuild_processes(algorithm, state)
        state["memory_map"] = self._build_memory_map(algorithm, state)
        state["stats"] = self._build_stats(algorithm, state)
        if any(
            event.get("type") == "queue"
            and event.get("name") == "created_processes"
            for event in events
        ):
            self._random_requests_by_algorithm[algorithm] = 0
        return state

    def latest_state(self, algorithm: str) -> dict[str, Any]:
        return self._state_by_algorithm.get(algorithm, {})

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
        self._active_algorithm = None

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
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._start_reader(self._process.stdout, self._stdout_queue)
        self._start_reader(self._process.stderr, self._stderr_queue)

    def _load_commands(self, algorithm: str, commands: list[str]) -> SimulationResult:
        command_lines = [
            self.build_config_command(algorithm, self.processes_for(algorithm)),
            *commands,
        ]
        result = SimulationResult(
            payload=self.build_payload(algorithm),
            command_lines=command_lines,
        )

        if not self.c_executable.exists():
            result.error = f"No existe el ejecutable: {self.c_executable}"
            return result

        try:
            if self.is_process_running() and self._active_algorithm != algorithm:
                self.close_process()
            self._ensure_process()
            self._active_algorithm = algorithm
            for line in command_lines:
                self.send_command(line)
        except OSError as exc:
            result.error = str(exc)

        return result

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

    def _apply_queue_event(self, state: dict[str, Any], event: dict[str, Any]) -> None:
        queue_name = str(event.get("name", ""))
        processes = list(event.get("processes", []))
        for process in processes:
            self._remove_pid_from_queues(state, int(process["pid"]), except_queue=queue_name)
        state["queues"][queue_name] = processes

    def _remove_pid_from_queues(
        self,
        state: dict[str, Any],
        pid: int,
        *,
        except_queue: str | None = None,
    ) -> None:
        for queue_name, processes in state["queues"].items():
            if queue_name == except_queue:
                continue
            state["queues"][queue_name] = [
                process for process in processes
                if int(process["pid"]) != pid
            ]

    def _rebuild_processes(self, algorithm: str, state: dict[str, Any]) -> None:
        pcb_by_pid: dict[int, dict[str, Any]] = {}
        for processes in state["queues"].values():
            for pcb in processes:
                pcb_by_pid[int(pcb["pid"])] = pcb

        running = state.get("running")
        if running is not None:
            pcb_by_pid[int(running["pid"])] = running

        previous_colors = {
            process.pid: process.color
            for process in self.processes_for(algorithm)
        }
        rebuilt = [
            self._ui_process_from_pcb(
                pcb,
                previous_colors.get(int(pcb.get("pid", 0))),
                state.get("snapshot", {}),
            )
            for _, pcb in sorted(pcb_by_pid.items())
        ]
        self._processes_by_algorithm[algorithm] = rebuilt
        if rebuilt:
            self._next_pid = max(process.pid for process in rebuilt) + 1

    def _ui_process_from_pcb(
        self,
        pcb: dict[str, Any],
        color: str | None,
        snapshot: dict[str, Any],
    ) -> UiProcess:
        scheduler = pcb.get("scheduler", {})
        memory = pcb.get("memory", {})
        cpu = pcb.get("cpu", {})
        interrupts = pcb.get("interrupts", {})
        burst = float(scheduler.get("burst_time", 0.0))
        remaining = max(0.0, float(scheduler.get("remaining_time", 0.0)))
        start = float(scheduler.get("start_time", -1.0))
        finish = float(scheduler.get("finish_time", -1.0))
        response = float(scheduler.get("response_time", 0.0))
        pid = int(pcb.get("pid", 0))

        return UiProcess(
            pid=pid,
            name=str(pcb.get("name", f"P{pid}")),
            burst_time=burst,
            memory=int(memory.get("required_kb", 0)),
            arrival_time=float(scheduler.get("arrival_time", 0.0)),
            priority=int(scheduler.get("priority", 0)),
            quantum=float(snapshot.get("quantum", 0.0)),
            state=str(pcb.get("state", "NEW")),
            remaining_time=remaining,
            assigned_blocks=int(memory.get("assigned_blocks", 0)),
            waste_kb=int(memory.get("waste_kb", 0)),
            program_counter=int(cpu.get("program_counter", 0)),
            memory_base=max(0, int(memory.get("start_block", 0))) * 4,
            memory_limit=max(0, int(memory.get("limit_block", 0))) * 4,
            progress=0.0 if burst <= 0 else (burst - remaining) / burst * 100.0,
            start_time=None if start < 0 else start,
            finish_time=None if finish < 0 else finish,
            waiting_time=float(scheduler.get("waiting_time", 0.0)),
            turnaround_time=float(scheduler.get("turnaround_time", 0.0)),
            response_time=None if start < 0 else response,
            interrupts=int(interrupts.get("completed", 0)),
            color=color or PROCESS_COLORS[pid % len(PROCESS_COLORS)],
        )

    def _build_memory_map(
        self,
        algorithm: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        memory = state.get("memory", {})
        block_size = int(memory.get("block_size_kb", 4))
        processes = {
            process.pid: process
            for process in self.processes_for(algorithm)
        }
        blocks = []
        for block in memory.get("blocks", []):
            owner = int(block.get("owner_pid", -1))
            process = processes.get(owner)
            blocks.append(
                {
                    "base_kb": int(block.get("start_block", 0)) * block_size,
                    "size_kb": int(block.get("length_blocks", 0)) * block_size,
                    "name": process.name if process else "Libre",
                    "color": process.color if process else "#30363d",
                }
            )
        return {
            "total_kb": int(memory.get("total_blocks", 0)) * block_size,
            "free_kb": int(memory.get("free_blocks", 0)) * block_size,
            "blocks": blocks,
        }

    def _build_stats(
        self,
        algorithm: str,
        state: dict[str, Any],
    ) -> dict[str, float]:
        processes = self.processes_for(algorithm)
        finished = [
            process for process in processes
            if process.state in {"TERMINATED", "ERROR"}
        ]
        current_time = float(state.get("snapshot", {}).get("current_time", 0.0))
        gantt_time = sum(
            float(segment.get("duration", 0.0))
            for segment in state.get("gantt", {}).get("segments", [])
        )

        def average(attribute: str) -> float:
            if not finished:
                return 0.0
            return sum(float(getattr(process, attribute) or 0.0) for process in finished) / len(finished)

        return {
            "avg_waiting": average("waiting_time"),
            "avg_turnaround": average("turnaround_time"),
            "avg_response": average("response_time"),
            "throughput": len(finished) / current_time if current_time > 0 else 0.0,
            "cpu_util": gantt_time / current_time * 100.0 if current_time > 0 else 0.0,
            "total_time": current_time,
        }

    def _sanitize_name(self, name: str) -> str:
        cleaned = "".join(ch for ch in name if not ch.isspace())
        return (cleaned or "P")[:15]

    def _color_for(self, pid: int) -> str:
        return PROCESS_COLORS[pid % len(PROCESS_COLORS)]

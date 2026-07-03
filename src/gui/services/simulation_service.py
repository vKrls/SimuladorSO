from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import queue
import subprocess
import threading
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
    last_swap_out: float | None = None
    last_swap_in: float | None = None
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


class SimulationService:
    def __init__(self, c_executable: Path | None = None):
        project_root = Path(__file__).resolve().parents[3]
        self.c_executable = c_executable or project_root / "build" / "simulator"
        self._next_pid_by_algorithm: dict[str, int] = {}
        self._processes_by_algorithm: dict[str, list[UiProcess]] = {}
        self._system_processes_by_algorithm: dict[str, list[UiProcess]] = {}
        self._random_process_count_by_algorithm: dict[str, int] = {}
        self._quantum_by_algorithm: dict[str, float] = {}
        self._speed_by_algorithm: dict[str, int] = {}
        self._switch_cost_by_algorithm: dict[str, float] = {}
        self._memory_algorithm = 0
        self._state_by_algorithm: dict[str, dict[str, Any]] = {}
        self._active_algorithm: str | None = None
        self._process: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str] = queue.Queue()
        self._stderr_queue: queue.Queue[str] = queue.Queue()
        self._reader_threads: list[threading.Thread] = []

    @property
    def memory_algorithm(self) -> int:
        return self._memory_algorithm

    @property
    def memory_algorithm_name(self) -> str:
        return MEMORY_ALGORITHM_NAMES[self._memory_algorithm]

    def set_memory_algorithm(self, algorithm: int) -> None:
        if algorithm not in MEMORY_ALGORITHM_NAMES:
            raise ValueError(f"Algoritmo de memoria inválido: {algorithm}")
        self._memory_algorithm = algorithm

    def configure_memory_algorithm(
        self,
        algorithm: str,
        memory_algorithm: int,
    ) -> SimulationResult:
        self.set_memory_algorithm(memory_algorithm)
        command = self.build_config_command(
            algorithm,
            self.processes_for(algorithm),
        )
        result = SimulationResult(
            payload={
                "memory_algorithm": self.memory_algorithm_name,
                "sent": False,
            },
            command_lines=[command],
        )

        if not self.is_process_running() or self._active_algorithm != algorithm:
            return result

        try:
            self.send_command(command)
            result.payload["sent"] = True
        except OSError as exc:
            result.error = str(exc)
        return result

    def switch_cost_for(self, algorithm: str) -> float:
        return self._switch_cost_by_algorithm.get(algorithm, 0.5)

    def configure_switch_cost(
        self,
        algorithm: str,
        switch_cost: float,
    ) -> SimulationResult:
        if switch_cost < 0:
            raise ValueError("El costo de cambio de contexto no puede ser negativo.")
        self._switch_cost_by_algorithm[algorithm] = switch_cost
        command = self.build_config_command(algorithm, self.processes_for(algorithm))
        result = SimulationResult(
            payload={"switch_cost": switch_cost, "sent": False},
            command_lines=[command],
        )
        if not self.is_process_running() or self._active_algorithm != algorithm:
            return result
        try:
            self.send_command(command)
            result.payload["sent"] = True
        except OSError as exc:
            result.error = str(exc)
        return result

    def quantum_for(self, algorithm: str) -> float:
        if algorithm != "round_robin":
            return 0.0
        return self._quantum_by_algorithm.get(algorithm, 5.0)

    def configure_quantum(self, algorithm: str, quantum: float) -> SimulationResult:
        if quantum <= 0:
            raise ValueError("El quantum debe ser mayor que cero.")
        self._quantum_by_algorithm[algorithm] = quantum
        for process in self._processes_by_algorithm.get(algorithm, []):
            process.quantum = quantum

        command = self.build_config_command(algorithm, self.processes_for(algorithm))
        result = SimulationResult(
            payload={"quantum": quantum, "sent": False},
            command_lines=[command],
        )
        if not self.is_process_running() or self._active_algorithm != algorithm:
            return result
        try:
            self.send_command(command)
            result.payload["sent"] = True
        except OSError as exc:
            result.error = str(exc)
        return result

    def processes_for(self, algorithm: str) -> list[UiProcess]:
        return list(self._processes_by_algorithm.get(algorithm, []))

    def system_processes_for(self, algorithm: str) -> list[UiProcess]:
        return list(self._system_processes_by_algorithm.get(algorithm, []))

    def add_process(self, algorithm: str, process_data: ProcessData) -> UiProcess:
        pid = self._next_pid_by_algorithm.get(algorithm, RESERVED_PID_COUNT)
        self._next_pid_by_algorithm[algorithm] = pid + 1
        process = UiProcess(
            pid=pid,
            name=self._sanitize_name(process_data.name.strip() or f"P{pid}"),
            burst_time=process_data.cpu_burst,
            memory=process_data.memory,
            arrival_time=process_data.arrival_time,
            priority=process_data.priority,
            quantum=self.quantum_for(algorithm)
            if algorithm == "round_robin"
            else process_data.quantum,
            color=self._color_for(pid),
        )
        self._processes_by_algorithm.setdefault(algorithm, []).append(process)
        return process

    def clear_processes(self, algorithm: str) -> None:
        self._processes_by_algorithm[algorithm] = []
        self._next_pid_by_algorithm[algorithm] = RESERVED_PID_COUNT
        self._random_process_count_by_algorithm[algorithm] = 0
        self._speed_by_algorithm.pop(algorithm, None)
        self._state_by_algorithm.pop(algorithm, None)

    def load_process(
        self,
        algorithm: str,
        process_data: ProcessData,
    ) -> tuple[UiProcess, SimulationResult]:
        process = self.add_process(algorithm, process_data)
        command = process.to_c_command()

        if self.is_process_running() and self._active_algorithm == algorithm:
            result = SimulationResult(
                payload=self.build_payload(algorithm),
                command_lines=[command],
            )
            try:
                self.send_command(command)
            except OSError as exc:
                result.error = str(exc)
        else:
            result = self._load_commands(algorithm, [command])
        return process, result

    def request_random_processes(
        self,
        algorithm: str,
        count: int,
    ) -> SimulationResult:
        count = max(1, min(20, count))
        self._random_process_count_by_algorithm[algorithm] = (
            self._random_process_count_by_algorithm.get(algorithm, 0) + count
        )
        return self._load_commands(algorithm, [f"RANDOM {count}"])

    def random_process_count_for(self, algorithm: str) -> int:
        return self._random_process_count_by_algorithm.get(algorithm, 0)

    def has_processes_for(self, algorithm: str) -> bool:
        return bool(self.processes_for(algorithm) or self.random_process_count_for(algorithm))

    def build_payload(self, algorithm: str) -> dict[str, Any]:
        return {
            "algorithm": algorithm,
            "memory_algorithm": self.memory_algorithm_name,
            "quantum": self.quantum_for(algorithm),
            "processes": [process.to_payload() for process in self.processes_for(algorithm)],
            "random_process_count": self._random_process_count_by_algorithm.get(algorithm, 0),
        }

    def build_c_commands(self, algorithm: str) -> list[str]:
        processes = self.processes_for(algorithm)
        return [
            self.build_config_command(algorithm, processes),
            f"SPEED {self._speed_by_algorithm.get(algorithm, 5)}",
            *[process.to_c_command() for process in processes],
            "RUN",
        ]

    def initialize(self, algorithm: str) -> SimulationResult:
        command_lines = [
            self.build_config_command(algorithm, self.processes_for(algorithm)),
            f"SPEED {self._speed_by_algorithm.get(algorithm, 5)}",
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

    def build_config_command(self, algorithm: str, processes: list[UiProcess]) -> str:
        sched_alg = {
            "fcfs": 0,
            "sjf_nonpreemptive": 1,
            "sjf_preemptive": 2,
            "round_robin": 3,
            "priority_nonpreemptive": 4,
            "priority_preemptive": 5,
        }.get(algorithm, 0)
        quantum = 0.0
        if algorithm == "round_robin":
            quantum = self.quantum_for(algorithm)
        switch_cost = self.switch_cost_for(algorithm)
        return (
            f"CONFIG {sched_alg} {self._memory_algorithm} "
            f"{quantum:.3f} {switch_cost:.3f}"
        )

    def run(self, algorithm: str, *, apply_events: bool = True) -> SimulationResult:
        payload = self.build_payload(algorithm)
        if self.is_process_running() and self._active_algorithm == algorithm:
            processes = self.processes_for(algorithm)
            command_lines = [
                self.build_config_command(algorithm, processes),
                f"SPEED {self._speed_by_algorithm.get(algorithm, 5)}",
                "RUN",
            ]
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

    def send_speed(self, algorithm: str, speed: int) -> SimulationResult:
        self._speed_by_algorithm[algorithm] = speed
        if not self.is_process_running() or self._active_algorithm != algorithm:
            return SimulationResult(payload={}, command_lines=[f"SPEED {speed}"])
        return self._send_control(f"SPEED {speed}")

    def send_raw_command(self, command: str) -> SimulationResult:
        return self._send_control(command)

    def stop(self) -> SimulationResult:
        result = self._send_control("STOP")
        if result.ok and self._process is not None:
            try:
                self._process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.close_process()
            else:
                self._join_reader_threads()
                self._process = None
                self._active_algorithm = None
        return result

    def read_stdout_lines(self) -> list[str]:
        self._join_readers_if_exited()
        return self._drain(self._stdout_queue)

    def read_stderr_lines(self) -> list[str]:
        self._join_readers_if_exited()
        return self._drain(self._stderr_queue)

    def parse_event(self, line: str, algorithm: str) -> dict[str, Any] | None:
        prefix = "SIM_DATA "
        if not line.startswith(prefix):
            return None

        try:
            event = json.loads(line[len(prefix):])
        except json.JSONDecodeError:
            return None

        if event.get("type") == "state":
            gantt = event.get("gantt", {})
            self._apply_gantt_colors(algorithm, gantt.get("segments", []))
        elif event.get("type") == "gantt":
            self._apply_gantt_colors(algorithm, event.get("segments", []))

        return event

    def _apply_gantt_colors(
        self,
        algorithm: str,
        segments: list[dict[str, Any]],
    ) -> None:
        colors_by_name = {
            process.name: process.color
            for process in self.processes_for(algorithm)
        }
        for segment in segments:
            kind = str(segment.get("kind", "PROCESS"))
            if kind == "IDLE":
                segment["color"] = "#30363d"
                continue
            if kind == "CONTEXT_SWITCH":
                segment["color"] = "#f7c59f"
                continue

            pid = int(segment.get("pid", 0))
            name = str(segment.get("name", f"P{pid}"))
            segment["color"] = colors_by_name.get(
                name,
                PROCESS_COLORS[pid % len(PROCESS_COLORS)],
            )

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
            if event_type == "state":
                state["snapshot"] = {
                    "current_time": event.get("current_time", 0.0),
                    "simulator_state": event.get("simulator_state", 1),
                    "cpu_busy": event.get("cpu_busy", False),
                    "quantum": event.get("config", {}).get("quantum", 0.0),
                    "switch_cost": event.get("config", {}).get("switch_cost", 0.0),
                    "snapshot_interval_ms": event.get("config", {}).get(
                        "snapshot_interval_ms",
                        100,
                    ),
                    "block_size_kb": event.get("memory", {}).get(
                        "block_size_kb",
                        4,
                    ),
                }
                state["state_event"] = event
                state["memory"] = event.get("memory", {})
                state["gantt"] = event.get("gantt", {})
                state["stats"] = event.get("stats", {})
                processes_by_pid = {
                    int(process.get("pid", -1)): process
                    for process in event.get("processes", [])
                }
                running_pid = event.get("running_pid")
                state["running"] = (
                    processes_by_pid.get(int(running_pid))
                    if running_pid is not None
                    else None
                )
                state["queues"] = event.get("queues", {})
            elif event_type == "snapshot":
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
        if not state.get("stats"):
            state["stats"] = self._build_stats(algorithm, state)
        if any(event.get("type") == "state" for event in events) or any(
            event.get("type") == "queue"
            and event.get("name") == "created_processes"
            for event in events
        ):
            self._random_process_count_by_algorithm[algorithm] = 0
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
        self._join_reader_threads()
        self._process = None
        self._active_algorithm = None

    def _ensure_process(self) -> None:
        if self.is_process_running():
            return

        self._stdout_queue = queue.Queue()
        self._stderr_queue = queue.Queue()
        self._reader_threads = []
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

    def _load_commands(self, algorithm: str, commands: list[str]) -> SimulationResult:
        command_lines = [
            self.build_config_command(algorithm, self.processes_for(algorithm)),
            f"SPEED {self._speed_by_algorithm.get(algorithm, 5)}",
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
        self._reader_threads.append(thread)

    def _join_readers_if_exited(self) -> None:
        if self._process is not None and self._process.poll() is not None:
            self._join_reader_threads()

    def _join_reader_threads(self) -> None:
        for thread in self._reader_threads:
            thread.join(timeout=0.1)

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
        state_event = state.get("state_event", {})
        if state_event:
            pcb_by_pid = {
                int(pcb["pid"]): pcb
                for pcb in state_event.get("processes", [])
            }
        else:
            for processes in state["queues"].values():
                if not isinstance(processes, list):
                    continue
                for pcb in processes:
                    if isinstance(pcb, dict):
                        pcb_by_pid[int(pcb["pid"])] = pcb

            running = state.get("running")
            if running is not None:
                pcb_by_pid[int(running["pid"])] = running

        previous_colors = {
            process.pid: process.color
            for process in (
                self.processes_for(algorithm)
                + self.system_processes_for(algorithm)
            )
        }
        rebuilt = [
            self._ui_process_from_pcb(
                pcb,
                previous_colors.get(int(pcb.get("pid", 0))),
                state.get("snapshot", {}),
            )
            for _, pcb in sorted(pcb_by_pid.items())
        ]
        self._system_processes_by_algorithm[algorithm] = [
            process for process in rebuilt if process.is_system
        ]
        user_processes = [
            process for process in rebuilt if not process.is_system
        ]
        self._processes_by_algorithm[algorithm] = user_processes
        if user_processes:
            self._next_pid_by_algorithm[algorithm] = (
                max(process.pid for process in user_processes) + 1
            )

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
        io = pcb.get("io", {})
        error = pcb.get("error", {})
        burst = float(scheduler.get("burst_time", 0.0))
        remaining = max(0.0, float(scheduler.get("remaining_time", 0.0)))
        start = float(scheduler.get("start_time", -1.0))
        finish = float(scheduler.get("finish_time", -1.0))
        response = float(scheduler.get("response_time", 0.0))
        pid = int(pcb.get("pid", 0))
        block_size = int(
            snapshot.get("block_size_kb", 4)
            if snapshot
            else 4
        )
        last_swap_out = float(pcb.get("last_swap_out", -1.0))
        last_swap_in = float(pcb.get("last_swap_in", -1.0))
        error_time = float(error.get("occurred_at", -1.0))

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
            memory_base=max(0, int(memory.get("start_block", 0))) * block_size,
            memory_limit=max(0, int(memory.get("limit_block", 0))) * block_size,
            progress=0.0 if burst <= 0 else (burst - remaining) / burst * 100.0,
            start_time=None if start < 0 else start,
            finish_time=None if finish < 0 else finish,
            ready_time=float(scheduler.get("ready_time", 0.0)),
            turnaround_time=float(scheduler.get("turnaround_time", 0.0)),
            response_time=None if start < 0 else response,
            interrupts=int(interrupts.get("total", 0)),
            planned_interrupts=int(interrupts.get("planned", 0)),
            interrupt_history=list(interrupts.get("history", [])),
            interrupt_breakdown=dict(interrupts.get("by_type", {})),
            is_system=bool(pcb.get("is_system", False)),
            resident=bool(pcb.get("resident", False)),
            memory_block_address=str(memory.get("block_address", "0x0")),
            memory_segments=list(memory.get("segments", [])),
            io_device=str(io.get("device", "NONE")),
            io_remaining=max(0.0, float(io.get("remaining_time", 0.0))),
            blocked_time=float(scheduler.get("blocked_time", 0.0)),
            nonresident_time=float(scheduler.get("nonresident_time", 0.0)),
            cpu_time=float(scheduler.get("cpu_time", 0.0)),
            context_switches=int(scheduler.get("context_switches", 0)),
            swap_count=int(pcb.get("swap_count", 0)),
            last_swap_out=None if last_swap_out < 0 else last_swap_out,
            last_swap_in=None if last_swap_in < 0 else last_swap_in,
            error_code=str(error.get("code", "")),
            error_description=str(error.get("description", "")),
            error_time=None if error_time < 0 else error_time,
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
            for process in (
                self.processes_for(algorithm)
                + self.system_processes_for(algorithm)
            )
        }
        blocks = []
        for block in memory.get("blocks", []):
            raw_owner = block.get("owner_pid")
            owner = int(raw_owner) if raw_owner is not None else -1
            process = processes.get(owner)
            is_system = bool(block.get("is_system", False))
            blocks.append(
                {
                    "base_kb": int(block.get("start_block", 0)) * block_size,
                    "size_kb": int(block.get("length_blocks", 0)) * block_size,
                    "name": process.name if process else str(block.get("owner_name", "Libre")),
                    "color": (
                        "#c77dff"
                        if is_system
                        else process.color if process else "#30363d"
                    ),
                }
            )
        return {
            "total_kb": int(memory.get("total_kb", TOTAL_MEMORY_KB)),
            "free_kb": int(memory.get("free_kb", TOTAL_MEMORY_KB)),
            "os_reserved_kb": int(memory.get("os_reserved_kb", 0)),
            "block_size_kb": block_size,
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
            if process.state == "TERMINATED"
        ]
        current_time = float(state.get("snapshot", {}).get("current_time", 0.0))
        gantt_time = sum(
            float(segment.get("duration", 0.0))
            for segment in state.get("gantt", {}).get("segments", [])
            if segment.get("kind", "PROCESS") == "PROCESS"
        )

        def average(attribute: str) -> float:
            if not finished:
                return 0.0
            return sum(float(getattr(process, attribute) or 0.0) for process in finished) / len(finished)

        return {
            "avg_ready_time": average("ready_time"),
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

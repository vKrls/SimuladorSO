from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from gui.application.command_serializer import SimulatorCommandSerializer
from gui.domain.models import ProcessData, SimulationResult, UiProcess
from gui.infrastructure.c_process_gateway import CProcessGateway
from gui.infrastructure.simulator_protocol_parser import SimulatorProtocolParser
from gui.mappers.process_mapper import ProcessMapper
from gui.state.simulation_session_store import SimulationSessionStore
from gui.state.simulation_state_reducer import SimulationStateReducer


def resolve_c_executable(build_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit

    is_windows = sys.platform.startswith("win")
    candidates = [
        build_dir / ("simulator.exe" if is_windows else "simulator"),
        build_dir / ("main.exe" if is_windows else "main"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


class SimulationService:
    def __init__(self, c_executable: Path | None = None):
        project_root = Path(__file__).resolve().parents[3]
        executable = resolve_c_executable(project_root / "build", c_executable)
        self.gateway = CProcessGateway(executable)
        self.store = SimulationSessionStore()
        self.commands = SimulatorCommandSerializer()
        self.parser = SimulatorProtocolParser()
        self.process_mapper = ProcessMapper()
        self.state_reducer = SimulationStateReducer(self.process_mapper)
        self._active_algorithm: str | None = None

    @property
    def c_executable(self) -> Path:
        return self.gateway.executable

    @property
    def memory_algorithm(self) -> int:
        return self.store.memory_algorithm

    @property
    def memory_algorithm_name(self) -> str:
        return self.store.memory_algorithm_name

    def set_memory_algorithm(self, algorithm: int) -> None:
        self.store.set_memory_algorithm(algorithm)

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
        return self.store.switch_cost_for(algorithm)

    def configure_switch_cost(
        self,
        algorithm: str,
        switch_cost: float,
    ) -> SimulationResult:
        if switch_cost < 0:
            raise ValueError("El costo de cambio de contexto no puede ser negativo.")
        self.store.set_switch_cost(algorithm, switch_cost)
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
        return self.store.quantum_for(algorithm)

    def configure_quantum(self, algorithm: str, quantum: float) -> SimulationResult:
        if quantum <= 0:
            raise ValueError("El quantum debe ser mayor que cero.")
        self.store.set_quantum(algorithm, quantum)
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
        return self.store.processes_for(algorithm)

    def system_processes_for(self, algorithm: str) -> list[UiProcess]:
        return self.store.system_processes_for(algorithm)

    def add_process(self, algorithm: str, process_data: ProcessData) -> UiProcess:
        pid = self.store.next_pid_for(algorithm)
        self.store.set_next_pid(algorithm, pid + 1)
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
            text_percent=process_data.text_percent,
            data_percent=process_data.data_percent,
            dynamic_percent=process_data.dynamic_percent,
            color=self.process_mapper.color_for(pid),
        )
        self.store.add_process(algorithm, process)
        return process

    def clear_processes(self, algorithm: str) -> None:
        self.store.clear_processes(algorithm)

    def load_process(
        self,
        algorithm: str,
        process_data: ProcessData,
    ) -> tuple[UiProcess, SimulationResult]:
        process = self.add_process(algorithm, process_data)
        command = self.commands.add_process(process)

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
        self.store.add_random_process_count(algorithm, count)
        return self._load_commands(
            algorithm,
            [self.commands.random_processes(count)],
        )

    def random_process_count_for(self, algorithm: str) -> int:
        return self.store.random_process_count_for(algorithm)

    def has_processes_for(self, algorithm: str) -> bool:
        return self.store.has_processes_for(algorithm)

    def build_payload(self, algorithm: str) -> dict[str, Any]:
        return {
            "algorithm": algorithm,
            "memory_algorithm": self.memory_algorithm_name,
            "quantum": self.quantum_for(algorithm),
            "speed": self.store.speed_for(algorithm),
            "processes": [
                process.to_payload()
                for process in self.processes_for(algorithm)
            ],
            "random_process_count": self.random_process_count_for(algorithm),
        }

    def build_c_commands(self, algorithm: str) -> list[str]:
        processes = self.processes_for(algorithm)
        return [
            self.build_config_command(algorithm, processes),
            *[self.commands.add_process(process) for process in processes],
            "RUN",
        ]

    def initialize(self, algorithm: str) -> SimulationResult:
        command_lines = [
            self.build_config_command(algorithm, self.processes_for(algorithm)),
        ]
        result = SimulationResult(
            payload=self.build_payload(algorithm),
            command_lines=command_lines,
        )
        self._send_command_lines(algorithm, command_lines, result)
        return result

    def build_config_command(self, algorithm: str, processes: list[UiProcess]) -> str:
        _ = processes
        quantum = self.quantum_for(algorithm) if algorithm == "round_robin" else 0.0
        return self.commands.config(
            algorithm,
            self.memory_algorithm,
            quantum,
            self.switch_cost_for(algorithm),
            self.store.speed_for(algorithm),
        )

    def run(self, algorithm: str, *, apply_events: bool = True) -> SimulationResult:
        _ = apply_events
        if self.is_process_running() and self._active_algorithm == algorithm:
            processes = self.processes_for(algorithm)
            command_lines = [
                self.build_config_command(algorithm, processes),
                "RUN",
            ]
        else:
            command_lines = self.build_c_commands(algorithm)
        result = SimulationResult(
            payload=self.build_payload(algorithm),
            command_lines=command_lines,
        )
        self._send_command_lines(algorithm, command_lines, result)
        return result

    def send_pause(self) -> SimulationResult:
        return self._send_control("PAUSE")

    def send_run(self) -> SimulationResult:
        return self._send_control("RUN")

    def send_speed(self, algorithm: str, speed: int) -> SimulationResult:
        self.store.set_speed(algorithm, speed)
        command = self.build_config_command(algorithm, self.processes_for(algorithm))
        if not self.is_process_running() or self._active_algorithm != algorithm:
            return SimulationResult(payload={}, command_lines=[command])
        return self._send_control(command)

    def send_raw_command(self, command: str) -> SimulationResult:
        return self._send_control(command)

    def stop(self) -> SimulationResult:
        result = self._send_control("STOP")
        if result.ok and not self.gateway.wait_for_exit(timeout=0.5):
            self.close_process()
        elif result.ok:
            self._active_algorithm = None
        return result

    def read_stdout_lines(self) -> list[str]:
        return self.gateway.read_stdout_lines()

    def read_stderr_lines(self) -> list[str]:
        return self.gateway.read_stderr_lines()

    def parse_event(self, line: str, algorithm: str) -> dict[str, Any] | None:
        event = self.parser.parse(line)
        if event is None:
            return None

        if event.get("type") == "state":
            self.process_mapper.apply_gantt_colors(
                event.get("gantt", {}).get("segments", []),
                self.processes_for(algorithm),
            )
        elif event.get("type") == "gantt":
            self.process_mapper.apply_gantt_colors(
                event.get("segments", []),
                self.processes_for(algorithm),
            )
        return event

    def apply_events(
        self,
        algorithm: str,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self.state_reducer.apply(algorithm, events, self.store)

    def latest_state(self, algorithm: str) -> dict[str, Any]:
        return self.store.latest_state(algorithm)

    def is_process_running(self) -> bool:
        return self.gateway.is_running()

    def close_process(self) -> None:
        self.gateway.close()
        self._active_algorithm = None

    def send_command(self, line: str) -> None:
        self.gateway.send_command(line)

    def _load_commands(
        self,
        algorithm: str,
        commands: list[str],
    ) -> SimulationResult:
        command_lines = [
            self.build_config_command(algorithm, self.processes_for(algorithm)),
            *commands,
        ]
        result = SimulationResult(
            payload=self.build_payload(algorithm),
            command_lines=command_lines,
        )
        self._send_command_lines(algorithm, command_lines, result)
        return result

    def _send_command_lines(
        self,
        algorithm: str,
        command_lines: list[str],
        result: SimulationResult,
    ) -> None:
        if not self.c_executable.exists():
            result.error = f"No existe el ejecutable: {self.c_executable}"
            return

        try:
            if self.is_process_running() and self._active_algorithm != algorithm:
                self.close_process()
            self.gateway.start()
            self._active_algorithm = algorithm
            for line in command_lines:
                self.send_command(line)
        except OSError as exc:
            result.error = str(exc)

    def _send_control(self, command: str) -> SimulationResult:
        result = SimulationResult(payload={}, command_lines=[command])
        try:
            self.send_command(command)
        except OSError as exc:
            result.error = str(exc)
        return result

    def _sanitize_name(self, name: str) -> str:
        cleaned = "".join(ch for ch in name if not ch.isspace())
        return (cleaned or "P")[:15]

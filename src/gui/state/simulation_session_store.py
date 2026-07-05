from __future__ import annotations

from typing import Any

from gui.domain.models import MEMORY_ALGORITHM_NAMES, RESERVED_PID_COUNT, UiProcess


class SimulationSessionStore:
    def __init__(self) -> None:
        self._next_pid_by_algorithm: dict[str, int] = {}
        self._processes_by_algorithm: dict[str, list[UiProcess]] = {}
        self._system_processes_by_algorithm: dict[str, list[UiProcess]] = {}
        self._random_process_count_by_algorithm: dict[str, int] = {}
        self._quantum_by_algorithm: dict[str, float] = {}
        self._speed_by_algorithm: dict[str, int] = {}
        self._switch_cost_by_algorithm: dict[str, float] = {}
        self._state_by_algorithm: dict[str, dict[str, Any]] = {}
        self._memory_algorithm = 0

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

    def switch_cost_for(self, algorithm: str) -> float:
        return self._switch_cost_by_algorithm.get(algorithm, 0.5)

    def set_switch_cost(self, algorithm: str, switch_cost: float) -> None:
        self._switch_cost_by_algorithm[algorithm] = switch_cost

    def quantum_for(self, algorithm: str) -> float:
        if algorithm != "round_robin":
            return 0.0
        return self._quantum_by_algorithm.get(algorithm, 5.0)

    def set_quantum(self, algorithm: str, quantum: float) -> None:
        self._quantum_by_algorithm[algorithm] = quantum
        for process in self._processes_by_algorithm.get(algorithm, []):
            process.quantum = quantum

    def speed_for(self, algorithm: str) -> int:
        return self._speed_by_algorithm.get(algorithm, 5)

    def set_speed(self, algorithm: str, speed: int) -> None:
        self._speed_by_algorithm[algorithm] = speed

    def processes_for(self, algorithm: str) -> list[UiProcess]:
        return list(self._processes_by_algorithm.get(algorithm, []))

    def set_processes(self, algorithm: str, processes: list[UiProcess]) -> None:
        self._processes_by_algorithm[algorithm] = processes

    def add_process(self, algorithm: str, process: UiProcess) -> None:
        self._processes_by_algorithm.setdefault(algorithm, []).append(process)

    def system_processes_for(self, algorithm: str) -> list[UiProcess]:
        return list(self._system_processes_by_algorithm.get(algorithm, []))

    def set_system_processes(
        self,
        algorithm: str,
        processes: list[UiProcess],
    ) -> None:
        self._system_processes_by_algorithm[algorithm] = processes

    def next_pid_for(self, algorithm: str) -> int:
        return self._next_pid_by_algorithm.get(algorithm, RESERVED_PID_COUNT)

    def set_next_pid(self, algorithm: str, pid: int) -> None:
        self._next_pid_by_algorithm[algorithm] = pid

    def add_random_process_count(self, algorithm: str, count: int) -> None:
        self._random_process_count_by_algorithm[algorithm] = (
            self._random_process_count_by_algorithm.get(algorithm, 0) + count
        )

    def random_process_count_for(self, algorithm: str) -> int:
        return self._random_process_count_by_algorithm.get(algorithm, 0)

    def reset_random_process_count(self, algorithm: str) -> None:
        self._random_process_count_by_algorithm[algorithm] = 0

    def has_processes_for(self, algorithm: str) -> bool:
        return bool(
            self.processes_for(algorithm)
            or self.random_process_count_for(algorithm)
        )

    def clear_processes(self, algorithm: str) -> None:
        self._processes_by_algorithm[algorithm] = []
        self._next_pid_by_algorithm[algorithm] = RESERVED_PID_COUNT
        self._random_process_count_by_algorithm[algorithm] = 0
        self._speed_by_algorithm.pop(algorithm, None)
        self._state_by_algorithm.pop(algorithm, None)

    def ensure_state(self, algorithm: str) -> dict[str, Any]:
        return self._state_by_algorithm.setdefault(
            algorithm,
            {
                "queues": {},
                "running": None,
                "snapshot": {},
                "memory": {},
                "gantt": {},
                "memory_history": [],
                "memory_history_summary": {},
            },
        )

    def latest_state(self, algorithm: str) -> dict[str, Any]:
        return self._state_by_algorithm.get(algorithm, {})

from __future__ import annotations

from gui.domain.models import UiProcess

SCHEDULER_ALGORITHMS = {
    "fcfs": 0,
    "sjf_nonpreemptive": 1,
    "sjf_preemptive": 2,
    "round_robin": 3,
    "priority_nonpreemptive": 4,
    "priority_preemptive": 5,
}


class SimulatorCommandSerializer:
    def config(
        self,
        algorithm: str,
        memory_algorithm: int,
        quantum: float,
        switch_cost: float,
        speed: int,
    ) -> str:
        sched_alg = SCHEDULER_ALGORITHMS.get(algorithm, 0)
        return (
            f"SET_CONFIG {sched_alg} {memory_algorithm} "
            f"{quantum:.3f} {switch_cost:.3f} {speed}"
        )

    def add_process(self, process: UiProcess) -> str:
        return process.to_c_command()

    def random_processes(self, count: int) -> str:
        return f"RANDOM {count}"

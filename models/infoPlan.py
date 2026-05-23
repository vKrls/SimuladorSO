from dataclasses import dataclass

@dataclass
class InfoPlan:
    priority: int
    arrival_time: int
    burst_time: int
    remaining_time: int
    start_time: int
    finish_time: int
    waiting_time: int
    response_time: int
    turnaround_time: int
    quantum_remaining: int
    cpu_time_used: int
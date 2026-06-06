from dataclasses import dataclass

@dataclass
class Info_Scheduler:
    arrival_time: float = 0
    burst_time: float = 0
    remaining_time: float = 0
    start_time: float | None = None
    finish_time: float | None = None
    waiting_time: float = 0
    turnaround_time: float = 0
    response_time: float | None = None
    
    priority: int | None = None             # Para Prioridades
    quantum_remaining: float | None = None  # Para Round-Robin
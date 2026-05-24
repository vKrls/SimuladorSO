from dataclasses import dataclass

@dataclass
class Info_Scheduler:
    start_time: float | None = None
    finish_time: float | None = None
    waiting_time: float = 0
    turnaround_time: float = 0
    response_time: float = 0
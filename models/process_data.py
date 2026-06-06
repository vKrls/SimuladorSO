from dataclasses import dataclass

@dataclass
class Process_Data:
    name: str
    cpu_burst: float
    memory: int
    arrival_time: float
    priority: int = 0
    quantum: float = 0
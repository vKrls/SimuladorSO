from dataclasses import dataclass

@dataclass
class Pcb:
    pid: int
    state: str
    pc: int
    arrival_time: float
    cpu_burst: float
    remaining_time: float
    priority: int
    memory_required: int
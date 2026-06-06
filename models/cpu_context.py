from dataclasses import dataclass

@dataclass
class Cpu_Context:
    program_counter: int = 0
    stack_pointer: int = 0
    cpu_state: str = "IDLE"
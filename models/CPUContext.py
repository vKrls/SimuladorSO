from dataclasses import dataclass

@dataclass
class CPUContext:
    program_counter: int
    registers: dict[str, int]
    stack_pointer: int
    cpu_state: str

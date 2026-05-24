from dataclasses import dataclass, field

@dataclass
class Cpu_Context:
    registers: dict[str, int] = field(default_factory=dict[str, int])
    accumulator: int = 0
    instruction_register: str = ""
    stack_pointer: int = 0
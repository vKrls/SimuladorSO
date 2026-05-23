from dataclasses import dataclass

@dataclass
class InfoMem:
    required_memory: int
    base_address: int
    limit_address: int
    assigned_blocks: list[int]
    memory_waste: int
    is_loaded: bool
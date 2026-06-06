from dataclasses import dataclass

@dataclass
class Info_Memory:
    required_memory: int = 0
    base_address: int | None = None
    limit_address: int | None = None
    assigned_blocks: list[int] | None = None
    memory_waste: int = 0
    is_loaded: bool = False
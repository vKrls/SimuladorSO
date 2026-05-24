from dataclasses import dataclass

@dataclass
class Info_Io:
    has_io: bool = False
    device: str = ""
    io_start_time: float = 0
    io_duration: float = 0
    interrupt_code: str = ""
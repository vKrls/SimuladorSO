from dataclasses import dataclass

@dataclass
class InfoIO:
    ioState: str
    current_devide: str
    io_remainingTime: float
    requests: int
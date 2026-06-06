from abc import ABC, abstractmethod

from models.pcb import Pcb

class Scheduler(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def selectPcb(self) -> Pcb | None:
        pass
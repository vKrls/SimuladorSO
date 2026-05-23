from abc import ABC, abstractmethod

from models.process import Process

class Scheduler(ABC):

    @abstractmethod
    def selectProcess(self) -> Process | None:
        pass
from schedulers.Scheduler import Scheduler

from models.process import Process

class FCFS(Scheduler):
    def __init__(self, readyQueue: list[Process]):
        self.readyQueue = readyQueue
        self.current_time = 0


    def setReadyQueue(self, readyQueue: list[Process]):
        pass


    def saveProcess(self, process: Process):
        pass

    def selectProcess(self) -> Process | None:
        pass

    def alg(self):
        pass




            

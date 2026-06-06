from scheduler.job_scheduler import Job_Scheduler

from models.pcb import Pcb

from scheduler.cpu_scheduler.scheduler import Scheduler

class scheduler_fcfs(Scheduler):
    def __init__(self, job_scheduler: Job_Scheduler):
        super().__init__()
        self.job_scheduler = job_scheduler

        self.ready_queue = job_scheduler.ready_queue

    def select_pcb(self) -> Pcb | None:
        pcb = self.ready_queue.pop(0)

        pcb.state = "RUNNING"
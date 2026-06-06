from scheduler.job_scheduler import Job_Scheduler

class Dispatcher:
    def __init__(self, job_scheduler: Job_Scheduler):
        self.job_scheduler = job_scheduler

    
    def send_pcb(self):
        pass
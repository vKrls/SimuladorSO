import time

from schedulers.Scheduler import Scheduler

from models.process import Process

class FCFS(Scheduler):
    def __init__(self, readyQueue: list[Process]):
        self.readyQueue = readyQueue
        self.current_time = 0


    def setColaListos(self, readyQueue: list[Process]):
        self.readyQueue = readyQueue


    def saveProcess(self, process: Process):
        sched = process.pcb.scheduler_info
        sched.arrival_time = self.current_time

        self.readyQueue.append(process)


    def selectProcess(self) -> Process | None:
        if len(self.readyQueue) == 0:
            return None

        return self.readyQueue.pop(0)
    

    def alg(self):
        print("\nALGORITMO FCFS:")
        while True:
            process = self.selectProcess()
            if process == None: break

            sched = process.pcb.scheduler_info
            
            sched.start_time = self.current_time
            sched.response_time = sched.start_time - sched.arrival_time
            sched.waiting_time = sched.start_time - sched.arrival_time

            # self.current_time += sched.burst_time

            # sched.finish_time = sched.start_time + sched.burst_time
            # sched.turnaround_time = sched.finish_time - sched.arrival_time
            # sched.remaining_time = 0

            print(f"Tick: {self.current_time} | Pid: {process.pcb.pid} | Name: {process.name} | Burst Time: {sched.burst_time} | Remaining Time: {process.pcb.scheduler_info.remaining_time} | Start: {process.pcb.scheduler_info.start_time} | Finish: {process.pcb.scheduler_info.finish_time}")
            while sched.remaining_time > 0:
                print(f"Tick: {self.current_time} | Pid: {process.pcb.pid} | Name: {process.name} | Burst Time: {sched.burst_time} | Remaining Time: {process.pcb.scheduler_info.remaining_time} | Start: {process.pcb.scheduler_info.start_time} | Finish: {process.pcb.scheduler_info.finish_time}")
                
                self.current_time += 1
                sched.remaining_time -= 1

                time.sleep(1/20)




            

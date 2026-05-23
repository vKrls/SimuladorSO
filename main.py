from models.process import Process

from models.pcb import Pcb
from models.CPUContext import CPUContext
from models.infoPlan   import InfoPlan
from models.infoMem    import InfoMem
from models.infoIO     import InfoIO
from models.infoError  import InfoError

from schedulers.SchedulerFCFS import FCFS
# from schedulers.SchedulerSJF  import SJF


def main():
    print("Hola e")

    processQueue: list[Process] = []

    cpu_context = CPUContext(0, {"AX": 0, "BX": 0, "CX": 0, "DX": 0}, 0, "Hola")
    memory_info = InfoMem(500, 0, 500, [], 0, True)
    io_info = InfoIO("", "", 0, 0)
    error_info = InfoError(False)

    for i in range(5):
        scheduler_info = InfoPlan(0, 0, 100 - i * 20, 100 - i * 20, 0, 0, 0, 0, 0, 0, 0)        
        
        pcb = Pcb(i, 0, "LISTO", cpu_context, scheduler_info, memory_info, io_info, error_info)

        process = Process(pcb, f"P{i}", "USER", 50, 50, 50, 50, 200, 50, [])
        processQueue.append(process)

    fcfs = FCFS(processQueue)
    fcfs.alg()

    # sjf = SJF(processQueue)
    # sjf.alg()
    

if __name__ == "__main__": main()
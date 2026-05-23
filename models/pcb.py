from models.CPUContext import CPUContext
from models.infoPlan import InfoPlan
from models.infoMem import InfoMem
from models.infoIO import InfoIO
from models.infoError import InfoError

class Pcb: 
    def __init__(self, pid: int, ppid: int, state: str,
                 cpu_context: CPUContext,
                 scheduler_info: InfoPlan,
                 memory_info: InfoMem,
                 io_info: InfoIO,
                 error_info: InfoError
        ):
        
        self.pid = pid
        self.ppid = ppid
        self.state = state

        self.cpu_context = cpu_context
        self.scheduler_info = scheduler_info
        self.memory_info = memory_info
        self.io_info = io_info
        self.error_info = error_info


    def setState(self, new_state: str):
        self.state = new_state


    def setProgramCounter(self, value: int):
        self.cpu_context.program_counter = value


    def incrementProgramCounter(self):
        self.cpu_context.program_counter += 1


    def saveContext(self, registers: dict[str, int], program_counter: int, stack_pointer: int, cpu_state: str):
        self.cpu_context.registers = registers
        self.cpu_context.program_counter = program_counter
        self.cpu_context.stack_pointer = stack_pointer
        self.cpu_context.cpu_state = cpu_state


    def loadContext(self):
        pass


    def setMemoryInfo(self, base_address: int, limit_address: int, assigned_blocks: list[int], memory_waste: int):
        self.memory_info.base_address = base_address
        self.memory_info.limit_address = limit_address
        self.memory_info.assigned_blocks = assigned_blocks
        self.memory_info.memory_waste = memory_waste
    

    # def markStarted(self, time):
    #     pass


    # def markFinished(self, time, terminationReason):
    #     pass


    def setIOInfo(self, current_device: str, io_time: float):
        self.io_info.current_devide = current_device
        self.io_info.io_remainingTime = io_time


    def clearIOInfo(self):
        pass
    

    def setError(self, error_code: int, error_desc: str):
        self.error_info.error_code = error_code
        self.error_info.error_desc = error_desc


    def summary(self):
        pass
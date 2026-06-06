from models.pcb            import Pcb
from models.cpu_context    import Cpu_Context
from models.info_scheduler import Info_Scheduler
from models.info_memory    import Info_Memory

from models.process_data   import Process_Data

class Job_Scheduler:
    def __init__(self):
        self.pcb_queue: list[Pcb] = []
        self.ready_queue:   list[Pcb] = []
        self.blocked_queue: list[Pcb] = []
        self.finished_list: list[Pcb] = []
        self.next_pid: int = 1


    def create_process(self, process_data: Process_Data) -> Pcb:
        pid = self.next_pid
        self.next_pid += 1

        input_name = process_data.name.strip()
        name = f"P{pid}" if input_name == "" else input_name
        cpu_burst = process_data.cpu_burst
        memory = process_data.memory
        arrival_time = process_data.arrival_time
        quantum = process_data.quantum
        priority = process_data.priority

        cpu_context = Cpu_Context(
            program_counter=0,
            stack_pointer=0,
            cpu_state="IDLE"
        )

        info_scheduler = Info_Scheduler(
            arrival_time=arrival_time,
            burst_time=cpu_burst,
            remaining_time=cpu_burst,
            start_time=None,
            finish_time=None,
            waiting_time=0,
            response_time=None,
            turnaround_time=0,
            
            priority=priority,
            quantum_remaining=quantum
        )

        info_memory = Info_Memory(
            required_memory=memory,
            base_address=None,
            limit_address=None,
            assigned_blocks=[],
            memory_waste=0,
            is_loaded=False
        )

        pcb = Pcb(
            cpu_context=cpu_context,
            info_scheduler=info_scheduler,
            info_memory=info_memory,
            info_io=None,
            info_error=None,

            name=name,
            pid=pid,
            state="NEW"
        )

        self.pcb_queue.append(pcb)
        self.ready_queue.append(pcb)

        return pcb
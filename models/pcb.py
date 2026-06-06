from dataclasses import dataclass

from models.cpu_context    import Cpu_Context
from models.info_scheduler import Info_Scheduler
from models.info_memory    import Info_Memory
from models.info_io        import Info_Io
from models.info_error     import Info_Error

@dataclass
class Pcb:
    cpu_context: Cpu_Context
    info_scheduler: Info_Scheduler
    info_memory: Info_Memory
    info_io: Info_Io | None
    info_error: Info_Error | None
    
    name: str = ""
    pid: int = -1
    state: str = ""

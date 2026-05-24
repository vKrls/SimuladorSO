from dataclasses import dataclass

from models.pcb import Pcb
from models.cpu_context import Cpu_Context
from models.info_scheduler import Info_Scheduler
from models.info_io import Info_Io
from models.info_error import Info_Error

@dataclass
class Process:
    name: str
    
    pcb: Pcb
    cpu_context: Cpu_Context
    info_scheduler: Info_Scheduler
    info_io: Info_Io
    info_error: Info_Error
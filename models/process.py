from models.pcb import Pcb

class Process():
    def __init__(self, pcb: Pcb, name: str, type: str, text_size: int, data_size: int, heap_size: int, stack_size: int, total_size: int, total_instructions: int, requested_resources: list[str]):
        self.pcb = pcb
        self.name = name
        self.type = type
        self.text_size = text_size
        self.data_size = data_size
        self.heap_size = heap_size
        self.stack_size = stack_size
        self.total_size = total_size
        self.total_instructions = total_instructions
        self.requested_resources = requested_resources

    def progressPercentage(self):
        pass

    def isTerminated(self):
        pass
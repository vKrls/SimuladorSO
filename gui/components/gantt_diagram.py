from PySide6.QtWidgets import QWidget

# from models.pcb import Pcb

class Gantt_Diagram(QWidget):
    def __init__(self):
        super().__init__()

        self.segments = []
        self.setMaximumHeight(100)

    # def add_segment(self, pcb: Pcb):
        
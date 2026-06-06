from PySide6.QtWidgets import QWidget, QVBoxLayout

# from gui.components.gantt_diagram import Gantt_Diagram

class Execute_Tab(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)


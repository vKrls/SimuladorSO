from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget, QTabWidget, QLabel

from core.simulator import Simulator

from gui.components.process_queue import Process_Queue
from gui.components.process_input import Process_Input

# from gui.components.execute_tab import Execute_Tab

label_style = """
    font-size: 10px;
    color: "#BBBBBB";
"""

class Center(QWidget):
    def __init__(self, simulator: Simulator, alg: str = ""):
        super().__init__()
        self.simulator = simulator
        self.alg = alg

        layout = QVBoxLayout()
        self.setLayout(layout)

        splitter = QSplitter()

        splitter.addWidget(self._left())
        splitter.addWidget(self._right())

        layout.addWidget(splitter)


    def _left(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        process_input_label = QLabel("INGRESAR PROCESO")
        process_input_label.setStyleSheet(label_style)
        process_input_label.setFixedHeight(10)
        layout.addWidget(process_input_label)

        self.process_input = Process_Input(self.alg)
        layout.addWidget(self.process_input)

        process_queue_label = QLabel("COLA DE PROCESOS")
        process_queue_label.setStyleSheet(label_style)
        process_queue_label.setFixedHeight(10)
        layout.addWidget(process_queue_label)

        self.process_queue = Process_Queue(self.alg)
        layout.addWidget(self.process_queue)

        widget.setLayout(layout)

        return widget
    

    def _right(self) -> QTabWidget:
        widget = QTabWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # self.execute_tab = Execute_Tab()
        # layout.addWidget(self.execute_tab)

        return widget
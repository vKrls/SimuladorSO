from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

process_style = """color: #03A9F4;"""
memory_style = """color: #FFC107;"""
algorithm_style = """color: #03A9F4;"""

class Footer(QFrame):
    def __init__(self) -> None:
        super().__init__()

        self.setFixedHeight(52)

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        self.setLayout(layout)
 
        label_cpu = QLabel("Cpu →")
        label_cpu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cpu = QLabel("-")
        self.cpu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cpu.setFixedWidth(50)

        layout.addWidget(label_cpu)
        layout.addWidget(self.cpu)

        label_process = QLabel("Procesos:")
        label_process.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.process = QLabel("0")
        self.process.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.process.setStyleSheet(process_style)

        layout.addWidget(label_process)
        layout.addWidget(self.process)

        label_finished = QLabel("Terminados:")
        label_finished.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.finished = QLabel("0")
        self.finished.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.finished.setStyleSheet(process_style)

        layout.addWidget(label_finished)
        layout.addWidget(self.finished)

        label_memory = QLabel("Memoria libre:")
        label_memory.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.memory = QLabel("4096 KB")
        self.memory.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.memory.setStyleSheet(memory_style)

        layout.addWidget(label_memory)
        layout.addWidget(self.memory)

        layout.addStretch()

        label_algorithm = QLabel("Algoritmo:")
        label_algorithm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.algorithm = QLabel("-")
        self.algorithm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.algorithm.setStyleSheet(algorithm_style)

        layout.addWidget(label_algorithm)
        layout.addWidget(self.algorithm)
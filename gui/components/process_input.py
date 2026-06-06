from PySide6.QtWidgets import QSlider, QPushButton, QSpinBox, QDoubleSpinBox, QVBoxLayout, QLineEdit, QWidget, QGridLayout, QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from models.process_data import Process_Data

class Process_Input(QFrame):
    def __init__(self, alg: str = ""):
        super().__init__()
        self.alg = alg

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(self._input_area())
        layout.addWidget(self._btn_area())
        layout.addWidget(self._speed_area())
        layout.addWidget(self._clean_area())


    def _input_area(self) -> QWidget:
        widget = QWidget()
        grid = QGridLayout()
        widget.setLayout(grid)

        label_name = QLabel("Nombre:")
        label_cpu = QLabel("CPU Burst:")
        label_memory = QLabel("Memoria:")
        label_arrive = QLabel("Llegada:")

        grid.addWidget(label_name,   0, 0)
        grid.addWidget(label_cpu,    1, 0)
        grid.addWidget(label_memory, 2, 0)
        grid.addWidget(label_arrive, 3, 0)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("P1, P2, ...")

        self.input_cpu = QDoubleSpinBox()
        self.input_cpu.setMinimum(1)
        self.input_cpu.setMaximum(999999)
        self.input_cpu.setValue(10.0)
        self.input_cpu.setSuffix(" u.t.")

        self.input_memory = QSpinBox()
        self.input_memory.setMinimum(1)
        self.input_memory.setMaximum(999999)
        self.input_memory.setValue(128)
        self.input_memory.setSuffix(" KB")

        self.input_arrival = QDoubleSpinBox()
        self.input_arrival.setMinimum(0.0)
        self.input_arrival.setMaximum(999999.9)
        self.input_arrival.setValue(0.0)
        self.input_arrival.setSuffix(" u.t.")

        if self.alg == "pr":
            label_priority = QLabel("Prioridad:")

            self.input_priority = QSpinBox()
            self.input_priority.setMinimum(0)
            self.input_priority.setMaximum(5)
            self.input_priority.setValue(5)

            grid.addWidget(label_priority,      4, 0)
            grid.addWidget(self.input_priority, 4, 1)

        if self.alg == "rr":
            quantum_label = QLabel("Quantum:")
            quantum_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.input_quantum = QDoubleSpinBox()
            self.input_quantum.setMinimum(0.01)
            self.input_quantum.setMaximum(500)
            self.input_quantum.setValue(5.0)
            self.input_quantum.setSuffix(" u.t.")

            grid.addWidget(quantum_label,      4, 0)
            grid.addWidget(self.input_quantum, 4, 1)

        grid.addWidget(self.input_name,    0, 1)
        grid.addWidget(self.input_cpu,     1, 1)
        grid.addWidget(self.input_memory,  2, 1)
        grid.addWidget(self.input_arrival, 3, 1)
        
        return widget
    

    def _btn_area(self) -> QWidget:
        widget = QWidget()
        grid = QGridLayout()
        widget.setLayout(grid)

        self.btn_add    = QPushButton("✚ Agregar Proceso")
        self.btn_random = QPushButton("🎲 Aleatorio")
        self.btn_start  = QPushButton("▶ Iniciar FCFS")
        self.btn_stop = QPushButton("⏸")
        self.btn_kill = QPushButton("⏹")

        grid.addWidget(self.btn_add, 0, 0, 1, 3)
        grid.addWidget(self.btn_random, 0, 3, 1, 3)
        grid.addWidget(self.btn_start, 1, 0, 1, 4)
        grid.addWidget(self.btn_stop, 1, 4)
        grid.addWidget(self.btn_kill, 1, 5)

        return widget
    

    def _speed_area(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)

        label_speed = QLabel("Velocidad:")
        label_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setMinimum(1)
        self.slider_speed.setMaximum(20)
        self.slider_speed.setValue(5)

        self.value_speed = QLabel("5x")
        self.value_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(label_speed)
        layout.addWidget(self.slider_speed)
        layout.addWidget(self.value_speed)
        
        return widget
    

    def _clean_area(self) -> QPushButton:
        self.btn_clean = QPushButton("🗑 Limpiar Todo")
        return self.btn_clean
    

    def get_process_data(self):
        process_data = Process_Data(
            name=self.input_name.text(),
            cpu_burst=self.input_cpu.value(),
            memory=self.input_memory.value(),
            arrival_time=self.input_arrival.value()
        )
        if self.alg == "rr": process_data.quantum = self.input_quantum.value()
        if self.alg == "pr": process_data.priority = self.input_priority.value()

        return process_data
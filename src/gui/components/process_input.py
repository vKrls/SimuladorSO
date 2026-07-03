from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.domain.models import ProcessData


class Process_Input(QGroupBox):
    def __init__(self, alg: str = ""):
        super().__init__("INGRESAR PROCESO")
        self.alg = alg

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self._input_area())
        layout.addWidget(self._button_area())
        layout.addWidget(self._speed_area())
        self.btn_clean = QPushButton("Limpiar todo")
        self.btn_clean.setObjectName("dangerButton")
        layout.addWidget(self.btn_clean)

    def _input_area(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setSpacing(6)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("P1, P2, ...")
        form.addRow("Nombre:", self.input_name)

        self.input_cpu = QDoubleSpinBox()
        self.input_cpu.setRange(1.0, 9999.0)
        self.input_cpu.setDecimals(1)
        self.input_cpu.setValue(10.0)
        self.input_cpu.setSuffix(" u.t.")
        form.addRow("CPU Burst:", self.input_cpu)

        self.input_memory = QSpinBox()
        self.input_memory.setRange(4, 896)
        self.input_memory.setSingleStep(4)
        self.input_memory.setValue(64)
        self.input_memory.setSuffix(" MB")
        form.addRow("Memoria:", self.input_memory)

        self.input_arrival = QDoubleSpinBox()
        self.input_arrival.setRange(0.0, 9999.0)
        self.input_arrival.setDecimals(1)
        self.input_arrival.setValue(0.0)
        self.input_arrival.setSuffix(" u.t.")
        form.addRow("Llegada:", self.input_arrival)

        if self.alg == "pr":
            self.input_priority = QSpinBox()
            self.input_priority.setRange(0, 9)
            self.input_priority.setValue(3)
            form.addRow("Prioridad:", self.input_priority)

        if self.alg == "rr":
            self.input_quantum = QDoubleSpinBox()
            self.input_quantum.setRange(0.1, 500.0)
            self.input_quantum.setDecimals(1)
            self.input_quantum.setValue(5.0)
            self.input_quantum.setSuffix(" u.t.")
            form.addRow("Quantum:", self.input_quantum)

        return widget

    def _button_area(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top = QHBoxLayout()
        self.btn_add = QPushButton("Agregar proceso")
        self.btn_add.setObjectName("primaryButton")
        self.btn_random = QPushButton("Aleatorio")
        self.input_random_count = QSpinBox()
        self.input_random_count.setRange(1, 20)
        self.input_random_count.setValue(5)
        self.input_random_count.setFixedWidth(64)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_random)
        top.addWidget(self.input_random_count)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        self.btn_start = QPushButton("Iniciar simulación")
        self.btn_start.setObjectName("successButton")
        self.btn_stop = QPushButton("Pausar")
        self.btn_kill = QPushButton("Detener")
        self.btn_kill.setObjectName("dangerButton")
        bottom.addWidget(self.btn_start, 1)
        bottom.addWidget(self.btn_stop)
        bottom.addWidget(self.btn_kill)
        layout.addLayout(bottom)
        return widget

    def _speed_area(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Velocidad:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(1, 20)
        self.slider_speed.setValue(5)
        self.value_speed = QLabel("5x")
        self.value_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_speed.setStyleSheet("color: #00d4ff; min-width: 30px;")
        layout.addWidget(label)
        layout.addWidget(self.slider_speed, 1)
        layout.addWidget(self.value_speed)
        return widget

    def get_process_data(self) -> ProcessData:
        process_data = ProcessData(
            name=self.input_name.text(),
            cpu_burst=self.input_cpu.value(),
            memory=self.input_memory.value() * 1024,
            arrival_time=self.input_arrival.value(),
        )
        if self.alg == "rr":
            process_data.quantum = self.input_quantum.value()
        if self.alg == "pr":
            process_data.priority = self.input_priority.value()
        return process_data

    def clear_name(self) -> None:
        self.input_name.clear()

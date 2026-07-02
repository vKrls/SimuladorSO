from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from gui.components.visual_widgets import GlowLabel


class Header(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        self.btn_back = QPushButton("Volver")
        self.btn_back.setFixedWidth(86)
        layout.addWidget(self.btn_back)

        self.title = GlowLabel("Algoritmo", "#00d4ff", 14)
        layout.addWidget(self.title)

        self.desc = QLabel("Descripción")
        self.desc.setStyleSheet("color: #484f58; font-size: 10px;")
        layout.addWidget(self.desc)
        layout.addStretch()

        memory_label = QLabel("Memoria:")
        memory_label.setStyleSheet("color: #8b949e; font-size: 9px;")
        layout.addWidget(memory_label)

        self.memory_combo = QComboBox()
        self.memory_combo.addItem("First Fit", 0)
        self.memory_combo.addItem("Best Fit", 1)
        self.memory_combo.addItem("Worst Fit", 2)
        self.memory_combo.setFixedWidth(125)
        layout.addWidget(self.memory_combo)

        switch_label = QLabel("Cambio ctx:")
        switch_label.setStyleSheet("color: #8b949e; font-size: 9px;")
        layout.addWidget(switch_label)

        self.switch_cost = QDoubleSpinBox()
        self.switch_cost.setRange(0.0, 20.0)
        self.switch_cost.setDecimals(1)
        self.switch_cost.setSingleStep(0.1)
        self.switch_cost.setSuffix(" u.t.")
        self.switch_cost.setFixedWidth(94)
        layout.addWidget(self.switch_cost)

        self.btn_demo = QPushButton("Demo")
        self.btn_demo.setObjectName("primaryButton")
        self.btn_demo.setFixedWidth(68)
        layout.addWidget(self.btn_demo)

        sep = QLabel("|")
        sep.setStyleSheet("color: #21262d;")
        layout.addWidget(sep)

        self.total_time = GlowLabel("T: 0.0 u.t.", "#7bc67e", 10)
        self.total_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.total_time)

        state_sep = QLabel("|")
        state_sep.setStyleSheet("color: #21262d;")
        layout.addWidget(state_sep)

        self.state = QLabel("INACTIVO")
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state.setStyleSheet("color: #484f58; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.state)

    def set_state(self, text: str, color: str = "#8b949e") -> None:
        self.state.setText(text)
        self.state.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")

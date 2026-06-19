from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from gui.components.visual_widgets import GlowLabel


class Header(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.setFixedHeight(56)

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

        self.total_time = GlowLabel("T: 0.0 u.t.", "#7bc67e", 10)
        self.total_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.total_time)

        sep = QLabel("|")
        sep.setStyleSheet("color: #21262d;")
        layout.addWidget(sep)

        self.state = QLabel("INACTIVO")
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state.setStyleSheet("color: #484f58; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.state)

    def set_state(self, text: str, color: str = "#8b949e") -> None:
        self.state.setText(text)
        self.state.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")

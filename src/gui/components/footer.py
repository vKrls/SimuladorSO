from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class Footer(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(14)

        layout.addWidget(self._plain("CPU ->"))
        self.cpu = self._value("--", "#7bc67e", width=90)
        layout.addWidget(self.cpu)

        layout.addWidget(self._sep())
        layout.addWidget(self._plain("Procesos:"))
        self.process = self._value("0", "#00d4ff")
        layout.addWidget(self.process)

        layout.addWidget(self._sep())
        layout.addWidget(self._plain("Terminados:"))
        self.finished = self._value("0", "#7bc67e")
        layout.addWidget(self.finished)

        layout.addWidget(self._sep())
        layout.addWidget(self._plain("Memoria libre:"))
        self.memory = self._value("1024 MB", "#c77dff", width=90)
        layout.addWidget(self.memory)

        layout.addStretch()
        layout.addWidget(self._plain("Política:"))
        self.algorithm = self._value("--", "#00d4ff", width=340)
        layout.addWidget(self.algorithm)

    def _plain(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #8b949e; font-size: 10px;")
        return label

    def _value(self, text: str, color: str, width: int | None = None) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
        if width:
            label.setFixedWidth(width)
        return label

    def _sep(self) -> QLabel:
        label = QLabel("|")
        label.setStyleSheet("color: #21262d;")
        return label

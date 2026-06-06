from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

btn_style = """
    QPushButton {
        background-color: #2196F3;
        color: white;
    }
"""

title_style = """
    font-size: 28px;
    font-weight: bold;
"""

desc_style = """
    font-size: 14px;
    color: gray;
"""

class Header(QFrame):
    def __init__(self) -> None:
        super().__init__()

        self.setFixedHeight(52)

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        self.setLayout(layout)

        self.btn_back = QPushButton("Volver")
        self.btn_back.setStyleSheet(btn_style)
 
        self.title = QLabel("Título")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet(title_style)

        self.desc = QLabel("Descripción")
        self.desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc.setStyleSheet(desc_style)

        self.total_time = QLabel("0.0 u.t.")
        self.total_time.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sl = QLabel("   |   ")
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.state = QLabel("INACTIVO")
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.btn_back)
        layout.addWidget(self.title)
        layout.addWidget(self.desc)
        layout.addStretch()

        layout.addWidget(self.total_time)
        layout.addWidget(sl)
        layout.addWidget(self.state)
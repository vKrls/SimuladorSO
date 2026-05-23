from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

class FCFS_Window(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        main_layout.addWidget(self.build_header())
        main_layout.addWidget(self.build_splitter())
        main_layout.addWidget(self.build_bottom())


    def build_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout()

        header.setLayout(layout)

        title = QLabel("FCFS Scheduler")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            color: #2c3e50;
            font-family: 'Arial';
            font-size: 24px;
            font-weight: bold;
            background-color: #ecf0f1;
            border: 2px solid #3498db;
            padding: 10px;
        """)
        layout.addWidget(title)

        return header


    def build_splitter(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        widget.setLayout(layout)

        splitter = QSplitter()

        wid_left = QWidget()
        wid_right = QWidget()

        splitter.addWidget(wid_left)
        splitter.addWidget(wid_right)

        layout.addWidget(splitter)

        return widget


    def build_bottom(self) -> QWidget:
        bottom = QWidget()
        layout = QHBoxLayout()

        bottom.setLayout(layout)

        return bottom
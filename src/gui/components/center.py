from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from gui.components.execute_tab import Execute_Tab
from gui.components.process_input import Process_Input
from gui.components.process_queue import Process_Queue
from gui.services.simulation_service import SimulationService


class Center(QWidget):
    LEFT_PANEL_WIDTH = 480

    def __init__(self, client: SimulationService, alg: str = ""):
        super().__init__()
        self.client = client
        self.alg = alg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        left = self._left()
        left.setMinimumWidth(self.LEFT_PANEL_WIDTH)
        splitter.addWidget(left)
        splitter.addWidget(self._right())
        splitter.setSizes([self.LEFT_PANEL_WIDTH, 900])
        layout.addWidget(splitter)

    def _left(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.process_input = Process_Input(self.alg)
        self.process_queue = Process_Queue(self.alg)
        layout.addWidget(self.process_input)
        layout.addWidget(self.process_queue, 1)
        return widget

    def _right(self) -> Execute_Tab:
        self.execute_tab = Execute_Tab()
        return self.execute_tab

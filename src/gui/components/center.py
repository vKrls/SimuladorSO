from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from gui.components.execute_tab import Execute_Tab
from gui.components.process_input import Process_Input
from gui.components.process_table import ProcessTable
from gui.services.simulation_service import SimulationService


class Center(QWidget):
    LEFT_PANEL_WIDTH = ProcessTable.PANEL_WIDTH

    def __init__(self, client: SimulationService, alg: str = ""):
        super().__init__()
        self.client = client
        self.alg = alg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(2)
        left = self._left()
        left.setMinimumWidth(self.LEFT_PANEL_WIDTH)
        self.splitter.addWidget(left)
        self.splitter.addWidget(self._right())
        self.splitter.setCollapsible(0, False)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self._set_initial_splitter_size()
        QTimer.singleShot(0, self._set_initial_splitter_size)
        layout.addWidget(self.splitter)

    def _left(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.process_input = Process_Input(self.alg)
        self.process_table = ProcessTable(self.alg)
        layout.addWidget(self.process_input)
        layout.addWidget(self.process_table, 1)
        return widget

    def _right(self) -> Execute_Tab:
        self.execute_tab = Execute_Tab()
        return self.execute_tab

    def _set_initial_splitter_size(self) -> None:
        self.splitter.setSizes([self.LEFT_PANEL_WIDTH, 10000])

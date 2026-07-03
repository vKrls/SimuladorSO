from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGroupBox, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget

from gui.components.visual_widgets import StateChip
from gui.domain.models import UiProcess


class Process_Queue(QGroupBox):
    def __init__(self, alg: str = ""):
        super().__init__("COLA DE PROCESOS")
        self.alg = alg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        hint = QLabel(self._hint_text())
        hint.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(hint)
        layout.addWidget(self._process_queue(), 1)
        self.footer = QLabel("0 proceso(s) en cola")
        self.footer.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(self.footer)

    def _hint_text(self) -> str:
        if self.alg == "rr":
            return "Orden circular por quantum."
        if self.alg == "pr":
            return "Menor valor indica mayor prioridad."
        if self.alg == "sjf":
            return "Se prioriza el burst más corto disponible."
        return "Ordenado por llegada."

    def _process_queue(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.layout_process_queue = QVBoxLayout(container)
        self.layout_process_queue.setContentsMargins(0, 0, 0, 0)
        self.layout_process_queue.setSpacing(5)
        self.layout_process_queue.addStretch()
        scroll.setWidget(container)
        return scroll

    def _process_card(self, process: UiProcess) -> QFrame:
        widget = QFrame()
        widget.setObjectName("processCard")
        widget.setFixedHeight(128)
        widget.setStyleSheet(f"""
            QFrame#processCard {{
                background: #0d1117;
                border: 1px solid {process.color}55;
                border-left: 3px solid {process.color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.addWidget(self._top_card(process))
        layout.addWidget(self._mid_card(process))
        layout.addWidget(self._bar_card(process))
        layout.addWidget(self._bottom_card(process))
        return widget

    def _top_card(self, process: UiProcess) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(f"[PID {process.pid}] {process.name}")
        title.setStyleSheet(f"color: {process.color}; font-weight: bold; font-size: 11px;")
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(StateChip(process.state))
        return widget

    def _mid_card(self, process: UiProcess) -> QWidget:
        fields = [
            f"Burst: {self._fmt(process.burst_time)}",
            f"Rest: {self._fmt(process.remaining_time or 0)}",
            f"Mem KB: {process.memory}",
            f"In Mem: {self._yes_no(process.resident)}",
        ]
        return self._field_row(fields)

    def _bar_card(self, process: UiProcess) -> QProgressBar:
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(max(0, min(100, process.progress))))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(7)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: #161b22; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background: {process.color}; border-radius: 3px; }}
        """)
        return progress_bar

    def _bottom_card(self, process: UiProcess) -> QWidget:
        fields = [
            f"Lleg: {self._fmt(process.arrival_time)}",
            f"Inicio: {self._dash(process.start_time)}",
            f"TAT: {self._fmt(process.turnaround_time)}",
            f"PC: 0x{process.program_counter:X}",
            f"SP: 0x{process.stack_pointer:X}",
        ]
        return self._field_row(fields)

    def _field_row(self, fields: list[str]) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for field in fields:
            layout.addWidget(self._field_chip(field))
        layout.addStretch()
        return widget

    def _field_chip(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("""
            background: rgba(33, 150, 243, 0.12);
            border: 1px solid rgba(33, 150, 243, 0.30);
            border-radius: 4px;
            color: #8b949e;
            font-size: 9px;
            padding: 2px 6px;
        """)
        return label

    def add_process_card(self, process: UiProcess) -> None:
        self.layout_process_queue.insertWidget(self.layout_process_queue.count() - 1, self._process_card(process))
        self._update_footer()

    def set_processes(self, processes: list[UiProcess]) -> None:
        self.clear()
        for process in processes:
            self.add_process_card(process)

    def clear(self) -> None:
        while self.layout_process_queue.count() > 1:
            item = self.layout_process_queue.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._update_footer()

    def _update_footer(self) -> None:
        count = max(0, self.layout_process_queue.count() - 1)
        self.footer.setText(f"{count} proceso(s) en cola")

    def _fmt(self, value: float | int | None) -> str:
        if value is None:
            return "--"
        return f"{float(value):.1f}"

    def _dash(self, value: float | int | None) -> str:
        if value is None:
            return "--"
        return self._fmt(value)

    def _yes_no(self, value: bool) -> str:
        return "Sí" if value else "No"

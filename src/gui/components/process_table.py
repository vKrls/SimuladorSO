from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGroupBox, QHBoxLayout, QLabel, QProgressBar, QScrollArea, QVBoxLayout, QWidget

from gui.components.visual_widgets import StateChip
from gui.domain.models import UiProcess


class ProcessCard(QFrame):
    CARD_WIDTH = 444
    CARD_HEIGHT = 128
    TOP_CHIP_WIDTH = 98
    TOP_PRIORITY_CHIP_WIDTH = 80
    BOTTOM_CHIP_WIDTH = 76

    def __init__(self, process: UiProcess, *, show_priority: bool = False):
        super().__init__()
        self._show_priority = show_priority
        self._color = ""
        self._state = ""
        self.setObjectName("processCard")
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 8, 10, 8)

        self.title = QLabel()
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.state_chip = StateChip()
        layout.addWidget(self._top_card())

        top_label_count = 5 if self._show_priority else 4
        top_chip_width = self.TOP_PRIORITY_CHIP_WIDTH if self._show_priority else self.TOP_CHIP_WIDTH
        self.mid_labels = self._field_labels(top_label_count, top_chip_width)
        layout.addWidget(self._field_row(self.mid_labels))

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(7)
        layout.addWidget(self.progress_bar)

        self.bottom_labels = self._field_labels(5, self.BOTTOM_CHIP_WIDTH)
        layout.addWidget(self._field_row(self.bottom_labels))

        self.update_process(process)

    def update_process(self, process: UiProcess) -> None:
        self._set_color(process.color)
        self._set_text(self.title, f"[PID {process.pid}] {process.name}")
        if process.state != self._state:
            self.state_chip.set_state(process.state)
            self._state = process.state

        mid_values = [
            f"Burst: {self._fmt(process.burst_time)}",
            f"Rest: {self._fmt(process.remaining_time or 0)}",
            f"Mem: {self._memory_mb(process.memory)}",
            f"En Mem: {self._yes_no(process.resident)}",
        ]
        if self._show_priority:
            mid_values.append(f"Prio: {process.priority}")
        self._set_label_values(self.mid_labels, mid_values)
        self._set_label_values(
            self.bottom_labels,
            [
                f"Lleg: {self._fmt(process.arrival_time)}",
                f"Inicio: {self._dash(process.start_time)}",
                f"TAT: {self._fmt(process.turnaround_time)}",
                f"PC: 0x{process.program_counter:X}",
                f"SP: 0x{process.stack_pointer:X}",
            ],
        )

        progress = int(max(0, min(100, process.progress)))
        if self.progress_bar.value() != progress:
            self.progress_bar.setValue(progress)

    def _top_card(self) -> QWidget:
        widget = QWidget()
        widget.setFixedHeight(22)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.state_chip)
        return widget

    def _field_labels(self, count: int, width: int) -> list[QLabel]:
        return [self._field_chip(width) for _ in range(count)]

    def _field_row(self, labels: list[QLabel]) -> QWidget:
        widget = QWidget()
        widget.setFixedHeight(22)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for label in labels:
            layout.addWidget(label)
        layout.addStretch()
        return widget

    def _field_chip(self, width: int) -> QLabel:
        label = QLabel()
        label.setFixedWidth(width)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setStyleSheet("""
            background: rgba(33, 150, 243, 0.12);
            border: 1px solid rgba(33, 150, 243, 0.30);
            border-radius: 4px;
            color: #8b949e;
            font-size: 9px;
            padding: 2px 6px;
        """)
        return label

    def _set_color(self, color: str) -> None:
        if color == self._color:
            return
        self._color = color
        self.setStyleSheet(f"""
            QFrame#processCard {{
                background: #0d1117;
                border: 1px solid {color}55;
                border-left: 3px solid {color};
                border-radius: 6px;
            }}
        """)
        self.title.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ background: #161b22; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}
        """)

    def _set_label_values(self, labels: list[QLabel], values: list[str]) -> None:
        for label, value in zip(labels, values):
            self._set_text(label, value)

    def _set_text(self, label: QLabel, text: str) -> None:
        if label.text() != text:
            label.setText(text)

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

    def _memory_mb(self, value_kb: int) -> str:
        value_mb = float(value_kb) / 1024.0
        if value_mb < 10:
            return f"{value_mb:.2f} MB"
        return f"{value_mb:.1f} MB"


class ProcessTable(QGroupBox):
    PANEL_WIDTH = ProcessCard.CARD_WIDTH + 24

    def __init__(self, alg: str = ""):
        super().__init__("TABLA DE PROCESOS")
        self.alg = alg
        self._show_priority = alg == "pr" or "priority" in alg
        self._cards: dict[int, ProcessCard] = {}
        self.setMinimumWidth(self.PANEL_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        hint = QLabel(self._hint_text())
        hint.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(hint)
        layout.addWidget(self._process_table(), 1)
        self.footer = QLabel("0 proceso(s)")
        self.footer.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(self.footer)

    def _hint_text(self) -> str:
        if self.alg == "rr":
            return "Vista estable por PID; el orden de ejecucion lo decide Round Robin."
        if self.alg == "pr":
            return "Vista estable por PID; menor valor indica mayor prioridad."
        if self.alg == "sjf":
            return "Vista estable por PID; SJF prioriza el burst mas corto disponible."
        return "Vista estable de procesos enviados al simulador."

    def _process_table(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.layout_process_table = QVBoxLayout(container)
        self.layout_process_table.setContentsMargins(0, 0, 0, 0)
        self.layout_process_table.setSpacing(5)
        self.layout_process_table.addStretch()
        scroll.setWidget(container)
        return scroll

    def add_process_card(self, process: UiProcess) -> None:
        card = self._cards.get(process.pid)
        if card is None:
            card = ProcessCard(process, show_priority=self._show_priority)
            self._cards[process.pid] = card
            self.layout_process_table.insertWidget(self.layout_process_table.count() - 1, card)
        else:
            card.update_process(process)
        self._update_footer()

    def set_processes(self, processes: list[UiProcess]) -> None:
        ordered_processes = sorted(processes, key=lambda process: process.pid)
        self.setUpdatesEnabled(False)
        try:
            active_pids = {process.pid for process in ordered_processes}
            for pid in list(self._cards):
                if pid not in active_pids:
                    self._remove_card(pid)

            for index, process in enumerate(ordered_processes):
                card = self._cards.get(process.pid)
                if card is None:
                    card = ProcessCard(process, show_priority=self._show_priority)
                    self._cards[process.pid] = card
                    self.layout_process_table.insertWidget(index, card)
                else:
                    card.update_process(process)
                    current_index = self.layout_process_table.indexOf(card)
                    if current_index != index:
                        self.layout_process_table.takeAt(current_index)
                        self.layout_process_table.insertWidget(index, card)
        finally:
            self.setUpdatesEnabled(True)
        self._update_footer()

    def clear(self) -> None:
        self.setUpdatesEnabled(False)
        try:
            for pid in list(self._cards):
                self._remove_card(pid)
        finally:
            self.setUpdatesEnabled(True)
        self._update_footer()

    def _remove_card(self, pid: int) -> None:
        card = self._cards.pop(pid, None)
        if card is None:
            return
        self.layout_process_table.removeWidget(card)
        card.setParent(None)
        card.deleteLater()

    def _update_footer(self) -> None:
        self.footer.setText(f"{len(self._cards)} proceso(s)")

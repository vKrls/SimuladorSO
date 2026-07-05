from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from gui.domain.models import UiProcess


@dataclass(frozen=True)
class QueueColumn:
    key: str
    title: str
    subtitle: str
    pids: list[int]
    color: str


class ProcessQueuesCanvas(QWidget):
    COLUMN_WIDTH = 148
    COLUMN_GAP = 8
    HEADER_HEIGHT = 58
    CARD_HEIGHT = 74
    CARD_GAP = 18
    TOP_MARGIN = 18
    LEFT_MARGIN = 18
    BOTTOM_MARGIN = 28
    MIN_HEIGHT = 520

    def __init__(self):
        super().__init__()
        self.processes: list[UiProcess] = []
        self.system_processes: list[UiProcess] = []
        self.state: dict[str, Any] = {}
        self.columns: list[QueueColumn] = []
        self.setMinimumSize(self._canvas_width(), self.MIN_HEIGHT)

    def set_state(
        self,
        processes: list[UiProcess],
        system_processes: list[UiProcess],
        state: dict[str, Any],
    ) -> None:
        self.processes = processes
        self.system_processes = system_processes
        self.state = state
        self.columns = self._build_columns()
        self._resize_canvas()
        self.update()

    def clear(self) -> None:
        self.processes = []
        self.system_processes = []
        self.state = {}
        self.columns = []
        self._resize_canvas()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0d1117"))

        if not self.columns:
            painter.setPen(QColor("#6e7681"))
            painter.setFont(QFont("Inter", 11))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Sin procesos en colas",
            )
            return

        for index, column in enumerate(self.columns):
            x = self.LEFT_MARGIN + index * (self.COLUMN_WIDTH + self.COLUMN_GAP)
            self._paint_column(painter, column, x)
            if index < len(self.columns) - 1:
                self._paint_stage_arrow(painter, x + self.COLUMN_WIDTH, index)

    def _paint_column(self, painter: QPainter, column: QueueColumn, x: int) -> None:
        header = QRectF(x, self.TOP_MARGIN, self.COLUMN_WIDTH, self.HEADER_HEIGHT)
        color = QColor(column.color)

        painter.fillRect(header, QColor(color.red(), color.green(), color.blue(), 26))
        painter.setPen(QPen(color, 1.2))
        painter.drawRoundedRect(header, 5, 5)

        count_rect = QRectF(header.right() - 46, header.top() + 10, 32, 22)
        painter.fillRect(count_rect, color)
        painter.setPen(QColor("#081015"))
        painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        painter.drawText(count_rect, Qt.AlignmentFlag.AlignCenter, str(len(column.pids)))

        painter.setPen(QColor("#f2f7fb"))
        title_font = QFont("Inter", 11, QFont.Weight.Bold)
        painter.setFont(title_font)
        title = QFontMetrics(title_font).elidedText(
            column.title,
            Qt.TextElideMode.ElideRight,
            self.COLUMN_WIDTH - 64,
        )
        painter.drawText(
            QRectF(header.left() + 12, header.top() + 8, self.COLUMN_WIDTH - 64, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        painter.setPen(QColor("#a9b8c4"))
        subtitle_font = QFont("Inter", 8)
        painter.setFont(subtitle_font)
        subtitle = QFontMetrics(subtitle_font).elidedText(
            column.subtitle,
            Qt.TextElideMode.ElideRight,
            self.COLUMN_WIDTH - 24,
        )
        painter.drawText(
            QRectF(header.left() + 12, header.top() + 32, self.COLUMN_WIDTH - 24, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            subtitle,
        )

        if not column.pids:
            empty_rect = QRectF(
                x,
                self.TOP_MARGIN + self.HEADER_HEIGHT + self.CARD_GAP,
                self.COLUMN_WIDTH,
                self.CARD_HEIGHT,
            )
            painter.setPen(QPen(QColor("#30363d"), 1))
            painter.drawRoundedRect(empty_rect, 5, 5)
            painter.setPen(QColor("#5f6b76"))
            painter.setFont(QFont("Inter", 9))
            painter.drawText(empty_rect, Qt.AlignmentFlag.AlignCenter, "--")
            return

        for index, pid in enumerate(column.pids):
            y = self._card_y(index)
            card = QRectF(x, y, self.COLUMN_WIDTH, self.CARD_HEIGHT)
            process = self._process_by_pid(pid)
            self._paint_process_card(painter, card, process, pid, column.color, column.key)
            if index < len(column.pids) - 1:
                self._paint_queue_arrow(painter, card)

    def _paint_process_card(
        self,
        painter: QPainter,
        rect: QRectF,
        process: UiProcess | None,
        pid: int,
        color: str,
        queue_key: str,
    ) -> None:
        base = QColor(color)
        painter.fillRect(rect, QColor(base.red(), base.green(), base.blue(), 22))
        painter.setPen(QPen(base, 1))
        painter.drawRoundedRect(rect, 5, 5)

        if process is None:
            name = f"PID {pid}"
            line_1 = "Sin PCB"
            line_2 = "--"
            line_3 = "--"
        else:
            name = f"{process.name} ({process.pid})"
            line_1 = self._card_line_1(process, queue_key)
            line_2 = self._card_line_2(process)
            line_3 = self._card_line_3(process)

        name_font = QFont("Inter", 10, QFont.Weight.Bold)
        painter.setFont(name_font)
        painter.setPen(QColor("#f2f7fb"))
        name_text = QFontMetrics(name_font).elidedText(
            name,
            Qt.TextElideMode.ElideRight,
            int(rect.width()) - 18,
        )
        painter.drawText(
            QRectF(rect.left() + 9, rect.top() + 7, rect.width() - 18, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            name_text,
        )

        detail_font = QFont("Courier New", 8)
        painter.setFont(detail_font)
        painter.setPen(QColor("#c9d1d9"))
        for offset, text in enumerate([line_1, line_2, line_3]):
            rendered = QFontMetrics(detail_font).elidedText(
                text,
                Qt.TextElideMode.ElideRight,
                int(rect.width()) - 18,
            )
            painter.drawText(
                QRectF(rect.left() + 9, rect.top() + 28 + offset * 13, rect.width() - 18, 13),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                rendered,
            )

    def _paint_queue_arrow(self, painter: QPainter, card: QRectF) -> None:
        x = card.center().x()
        start = card.bottom() + 2
        end = card.bottom() + self.CARD_GAP - 4
        painter.setPen(QPen(QColor("#536171"), 1))
        painter.drawLine(int(x), int(start), int(x), int(end))
        self._paint_arrow_head(painter, x, end + 4, "down", "#536171")

    def _paint_stage_arrow(self, painter: QPainter, start_x: float, column_index: int) -> None:
        y = self.TOP_MARGIN + self.HEADER_HEIGHT / 2
        end_x = start_x + self.COLUMN_GAP - 6
        painter.setPen(QPen(QColor("#425466"), 1))
        painter.drawLine(int(start_x + 5), int(y), int(end_x), int(y))
        self._paint_arrow_head(painter, end_x + 5, y, "right", "#425466")

    def _paint_arrow_head(
        self,
        painter: QPainter,
        x: float,
        y: float,
        direction: str,
        color: str,
    ) -> None:
        if direction == "down":
            points = [(x, y), (x - 5, y - 8), (x + 5, y - 8)]
        else:
            points = [(x, y), (x - 8, y - 5), (x - 8, y + 5)]

        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(px, py) for px, py in points]))
        painter.setBrush(Qt.BrushStyle.NoBrush)

    def _build_columns(self) -> list[QueueColumn]:
        queues = dict(self.state.get("queues", {}))
        devices = queues.get("devices", {})
        blocked_pids: list[int] = []
        device_count = 0
        if isinstance(devices, dict):
            for pids in devices.values():
                device_pids = self._pid_list(pids)
                blocked_pids.extend(device_pids)
                device_count += len(device_pids)
        if not blocked_pids:
            blocked_pids = [
                process.pid
                for process in self.processes
                if process.state == "BLOCKED"
            ]

        running = self._running_pid()
        return [
            QueueColumn(
                "job",
                "job_q",
                "Llegaron; esperan memoria",
                self._pid_list(queues.get("job", [])),
                "#2a9d8f",
            ),
            QueueColumn(
                "ready",
                "ready_q",
                "Residentes; esperan CPU",
                self._pid_list(queues.get("ready", [])),
                "#2563eb",
            ),
            QueueColumn(
                "running",
                "running",
                "CPU actual",
                [] if running is None else [running],
                "#2e7d32",
            ),
            QueueColumn(
                "blocked",
                "device_q",
                f"E/S activa: {device_count}",
                blocked_pids,
                "#e65100",
            ),
            QueueColumn(
                "nonresident",
                "nonresident_q",
                "Fuera de memoria",
                self._pid_list(queues.get("nonresident", [])),
                "#8b5cf6",
            ),
            QueueColumn(
                "finished",
                "finished_q",
                "Terminados",
                self._finished_pids(queues),
                "#607d8b",
            ),
        ]

    def _resize_canvas(self) -> None:
        max_count = max((len(column.pids) for column in self.columns), default=0)
        content_height = (
            self.TOP_MARGIN
            + self.HEADER_HEIGHT
            + self.CARD_GAP
            + max(1, max_count) * self.CARD_HEIGHT
            + max(0, max_count - 1) * self.CARD_GAP
            + self.BOTTOM_MARGIN
        )
        self.setMinimumSize(self._canvas_width(), max(self.MIN_HEIGHT, content_height))
        self.resize(self.minimumSize())

    def _canvas_width(self) -> int:
        column_count = 6
        return (
            self.LEFT_MARGIN * 2
            + column_count * self.COLUMN_WIDTH
            + (column_count - 1) * self.COLUMN_GAP
        )

    def _card_y(self, index: int) -> int:
        return (
            self.TOP_MARGIN
            + self.HEADER_HEIGHT
            + self.CARD_GAP
            + index * (self.CARD_HEIGHT + self.CARD_GAP)
        )

    def _card_line_1(self, process: UiProcess, queue_key: str) -> str:
        if queue_key == "job":
            return f"Lleg {process.arrival_time:.1f} | Mem {self._memory(process.memory)}"
        if queue_key == "ready":
            return f"Rest {process.remaining_time or 0:.1f} | Ready {process.ready_time:.1f}"
        if queue_key == "running":
            return f"Rest {process.remaining_time or 0:.1f} | CPU {process.cpu_time:.1f}"
        if queue_key == "blocked":
            return f"{process.io_device} | I/O {process.io_remaining:.1f}"
        if queue_key == "nonresident":
            return f"Rest {process.remaining_time or 0:.1f} | Swaps {process.swap_count}"
        return f"TAT {process.turnaround_time:.1f} | CPU {process.cpu_time:.1f}"

    def _card_line_2(self, process: UiProcess) -> str:
        resident = "RAM" if process.resident else "swap"
        return f"{resident} | Prio {process.priority} | ctx {process.context_switches}"

    def _card_line_3(self, process: UiProcess) -> str:
        if process.error_code:
            return f"ERR {process.error_code}"
        return f"PC 0x{process.program_counter:X} | SP 0x{process.stack_pointer:X}"

    def _memory(self, value_kb: int) -> str:
        if value_kb >= 1024:
            return f"{value_kb / 1024:.1f}MB"
        return f"{value_kb}KB"

    def _running_pid(self) -> int | None:
        running = self.state.get("running")
        if isinstance(running, dict) and running.get("pid") is not None:
            return int(running["pid"])
        for process in self.processes:
            if process.state == "RUNNING":
                return process.pid
        return None

    def _finished_pids(self, queues: dict[str, Any]) -> list[int]:
        finished = self._pid_list(queues.get("finished", []))
        if finished:
            return finished
        return [
            process.pid
            for process in self.processes
            if process.state == "TERMINATED"
        ]

    def _process_by_pid(self, pid: int) -> UiProcess | None:
        for process in self.processes + self.system_processes:
            if process.pid == pid:
                return process
        return None

    def _pid_list(self, values: Any) -> list[int]:
        if not isinstance(values, list):
            return []
        pids: list[int] = []
        for value in values:
            try:
                pids.append(int(value))
            except (TypeError, ValueError):
                continue
        return pids


class ProcessQueuesTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.canvas = ProcessQueuesCanvas()
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)

    def set_state(
        self,
        processes: list[UiProcess],
        system_processes: list[UiProcess],
        state: dict[str, Any],
    ) -> None:
        self.canvas.set_state(processes, system_processes, state)

    def clear(self) -> None:
        self.canvas.clear()

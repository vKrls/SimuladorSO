from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QSizePolicy, QWidget

from gui.domain.models import PROCESS_COLORS

STATE_COLORS = {
    "NONE": "#6b7280",
    "NEW": "#546e7a",
    "READY": "#1565c0",
    "RUNNING": "#2e7d32",
    "BLOCKED": "#e65100",
    "TERMINATED": "#424242",
}

STATE_LABELS = {
    "NONE": "FUERA SO",
    "NEW": "NUEVO",
    "READY": "LISTO",
    "RUNNING": "EJECUTANDO",
    "BLOCKED": "BLOQUEADO",
    "TERMINATED": "TERMINADO",
}


class GlowLabel(QLabel):
    def __init__(self, text: str, color: str = "#00d4ff", font_size: int = 14, bold: bool = True):
        super().__init__(text)
        font = QFont("Courier New", font_size)
        font.setBold(bold)
        self.setFont(font)
        self.setStyleSheet(f"color: {color}; background: transparent;")
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(color))
        glow.setBlurRadius(16)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)


class StateChip(QLabel):
    def __init__(self, state: str = "NONE"):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(112)
        self.set_state(state)

    def set_state(self, state: str) -> None:
        color = STATE_COLORS.get(state, "#546e7a")
        label = STATE_LABELS.get(state, state)
        self.setText(label)
        self.setStyleSheet(f"""
            background: {color}22;
            color: {color};
            border: 1px solid {color};
            border-radius: 8px;
            padding: 2px 6px;
            font-family: 'Courier New';
            font-size: 8px;
            font-weight: bold;
        """)


class GanttWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.segments: list[dict] = []
        self.total_time = 1.0
        self.setMinimumHeight(104)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_segments(self, segments: list[dict], total_time: float | None = None) -> None:
        self.segments = segments
        if total_time is None:
            self.total_time = max(
                [1.0] + [float(seg.get("start", 0)) + float(seg.get("duration", 0)) for seg in segments]
            )
        else:
            self.total_time = max(1.0, float(total_time))
        self.update()

    def clear(self) -> None:
        self.segments = []
        self.total_time = 1.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        top_label_y = 3
        bar_y = 24
        bar_h = 40
        bottom_label_y = bar_y + bar_h + 7
        time_label_h = 16

        painter.fillRect(0, 0, width, height, QColor("#0d1117"))
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.drawLine(0, bar_y + bar_h, width, bar_y + bar_h)

        if not self.segments:
            painter.setPen(QColor("#6e7681"))
            painter.setFont(QFont("Courier New", 10))
            painter.drawText(0, 0, width, height, Qt.AlignmentFlag.AlignCenter, "[ Diagrama de Gantt ]")
            return

        for seg in self.segments:
            start = float(seg.get("start", 0))
            duration = float(seg.get("duration", 0))
            limit = float(seg.get("limit", start + duration))
            kind = str(seg.get("kind", "PROCESS"))
            if duration <= 0:
                continue

            x1 = int((start / self.total_time) * width)
            x2 = int((limit / self.total_time) * width)
            block_w = max(x2 - x1, 3)
            color = str(seg.get("color", "#00d4ff"))

            grad = QLinearGradient(x1, bar_y, x1, bar_y + bar_h)
            c = QColor(color)
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 220))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 90))
            painter.fillRect(x1, bar_y, block_w, bar_h, grad)
            painter.setPen(QPen(QColor(color), 1))
            painter.drawRect(x1, bar_y, block_w, bar_h)

            min_label_width = 12 if kind == "CONTEXT_SWITCH" else 28
            if block_w > min_label_width:
                painter.setPen(QColor("#ffffff"))
                font_size = 7 if kind == "CONTEXT_SWITCH" else 8
                painter.setFont(QFont("Courier New", font_size, QFont.Weight.Bold))
                painter.drawText(
                    x1 + 2,
                    bar_y,
                    block_w - 4,
                    bar_h,
                    Qt.AlignmentFlag.AlignCenter,
                    str(seg.get("name", ""))[:8],
                )

            if kind != "IDLE":
                painter.setPen(QColor("#8b949e"))
                painter.setFont(QFont("Courier New", 7))

                # Inicio debajo del extremo izquierdo del segmento.
                painter.drawLine(x1, bar_y + bar_h, x1, bar_y + bar_h + 4)
                painter.drawText(
                    x1 + 2,
                    bottom_label_y,
                    max(1, block_w - 4),
                    time_label_h,
                    Qt.AlignmentFlag.AlignLeft,
                    f"{start:.1f}",
                )

                # Límite encima del extremo derecho del segmento.
                painter.drawLine(x2, bar_y - 4, x2, bar_y)
                painter.drawText(
                    x1 + 2,
                    top_label_y,
                    max(1, block_w - 4),
                    time_label_h,
                    Qt.AlignmentFlag.AlignRight,
                    f"{limit:.1f}",
                )


class MemoryMapWidget(QWidget):
    def __init__(self, total_kb: int = 1024 * 1024):
        super().__init__()
        self.total_kb = total_kb
        self.blocks: list[dict] = []
        self.setMinimumHeight(86)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_blocks(self, blocks: list[dict], total_kb: int | None = None) -> None:
        if total_kb is not None:
            self.total_kb = total_kb
        self.blocks = blocks
        self.update()

    def clear(self) -> None:
        self.blocks = []
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        bar_h = 34
        bar_y = 24

        painter.fillRect(0, 0, width, self.height(), QColor("#0d1117"))
        painter.fillRect(0, bar_y, width, bar_h, QColor("#161b22"))
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.drawRect(0, bar_y, width - 1, bar_h)

        for block in self.blocks:
            base = int(block.get("base_kb", 0))
            size = int(block.get("size_kb", 0))
            color = str(block.get("color", "#00d4ff"))
            name = str(block.get("name", ""))
            if size <= 0:
                continue

            x1 = int((base / self.total_kb) * width) if self.total_kb else 0
            block_w = max(int((size / self.total_kb) * width), 2) if self.total_kb else 2
            c = QColor(color)
            grad = QLinearGradient(x1, bar_y, x1, bar_y + bar_h)
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 230))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 100))
            painter.fillRect(x1 + 1, bar_y + 1, max(1, block_w - 2), bar_h - 2, grad)

            if block_w > 26:
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Courier New", 7))
                painter.drawText(x1 + 2, bar_y, block_w - 4, bar_h, Qt.AlignmentFlag.AlignCenter, name[:7])

        painter.setPen(QColor("#8b949e"))
        painter.setFont(QFont("Courier New", 8))
        painter.drawText(0, 4, width, 16, Qt.AlignmentFlag.AlignLeft, "Memoria")
        total_text = (
            f"{self.total_kb / (1024 * 1024):.1f} GB"
            if self.total_kb >= 1024 * 1024
            else f"{self.total_kb / 1024:.0f} MB"
        )
        painter.drawText(
            0,
            bar_y + bar_h + 6,
            width,
            16,
            Qt.AlignmentFlag.AlignRight,
            f"Total: {total_text}",
        )

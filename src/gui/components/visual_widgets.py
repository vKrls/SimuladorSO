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
    FIT_MODE = "fit"
    SLIDE_MODE = "slide"
    SLIDE_PIXELS_PER_TIME_UNIT = 18
    DRAG_THRESHOLD_PX = 4

    def __init__(self):
        super().__init__()
        self.segments: list[dict] = []
        self.total_time = 1.0
        self.mode = self.SLIDE_MODE
        self.scroll_x = 0
        self._press_x = 0
        self._press_scroll_x = 0
        self._dragging = False
        self._auto_follow = True
        self.setMinimumHeight(104)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_segments(self, segments: list[dict], total_time: float | None = None) -> None:
        self.segments = segments
        if total_time is None:
            self.total_time = max(
                [1.0] + [float(seg.get("start", 0)) + float(seg.get("duration", 0)) for seg in segments]
            )
        else:
            self.total_time = max(1.0, float(total_time))
        if self.mode == self.SLIDE_MODE and self._auto_follow:
            self.scroll_x = self._max_scroll_x()
        else:
            self._clamp_scroll_x()
        self.update()

    def clear(self) -> None:
        self.segments = []
        self.total_time = 1.0
        self.scroll_x = 0
        self._auto_follow = True
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

        content_width = self._content_width()
        for seg in self.segments:
            start = float(seg.get("start", 0))
            duration = float(seg.get("duration", 0))
            limit = float(seg.get("limit", start + duration))
            kind = str(seg.get("kind", "PROCESS"))
            if duration <= 0:
                continue

            x1 = self._time_to_x(start, content_width)
            x2 = self._time_to_x(limit, content_width)
            block_w = max(x2 - x1, 3)
            visible_x1 = x1 - self.scroll_x
            visible_x2 = x2 - self.scroll_x
            if visible_x2 < 0 or visible_x1 > width:
                continue
            color = str(seg.get("color", "#00d4ff"))

            grad = QLinearGradient(visible_x1, bar_y, visible_x1, bar_y + bar_h)
            c = QColor(color)
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 220))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 90))
            painter.fillRect(visible_x1, bar_y, block_w, bar_h, grad)
            painter.setPen(QPen(QColor(color), 1))
            painter.drawRect(visible_x1, bar_y, block_w, bar_h)

            min_label_width = 12 if kind == "CONTEXT_SWITCH" else 28
            if block_w > min_label_width:
                painter.setPen(QColor("#ffffff"))
                font_size = 7 if kind == "CONTEXT_SWITCH" else 8
                painter.setFont(QFont("Courier New", font_size, QFont.Weight.Bold))
                painter.drawText(
                    visible_x1 + 2,
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
                painter.drawLine(visible_x1, bar_y + bar_h, visible_x1, bar_y + bar_h + 4)
                painter.drawText(
                    visible_x1 + 2,
                    bottom_label_y,
                    max(1, block_w - 4),
                    time_label_h,
                    Qt.AlignmentFlag.AlignLeft,
                    f"{start:.1f}",
                )

                # Límite encima del extremo derecho del segmento.
                painter.drawLine(visible_x2, bar_y - 4, visible_x2, bar_y)
                painter.drawText(
                    visible_x1 + 2,
                    top_label_y,
                    max(1, block_w - 4),
                    time_label_h,
                    Qt.AlignmentFlag.AlignRight,
                    f"{limit:.1f}",
                )

        if self.mode == self.SLIDE_MODE and content_width > width:
            self._paint_scrollbar(painter, content_width, width, height)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        self._press_x = int(event.position().x())
        self._press_scroll_x = self.scroll_x
        self._dragging = False
        self.setCursor(Qt.CursorShape.ClosedHandCursor if self.mode == self.SLIDE_MODE else Qt.CursorShape.PointingHandCursor)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.mode != self.SLIDE_MODE or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return

        delta_x = int(event.position().x()) - self._press_x
        if abs(delta_x) >= self.DRAG_THRESHOLD_PX:
            self._dragging = True
            self._auto_follow = False
            self.scroll_x = self._press_scroll_x - delta_x
            self._clamp_scroll_x()
            self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if not self._dragging:
            self._toggle_mode()

        self.setCursor(Qt.CursorShape.OpenHandCursor if self.mode == self.SLIDE_MODE else Qt.CursorShape.PointingHandCursor)
        event.accept()

    def wheelEvent(self, event) -> None:
        if self.mode != self.SLIDE_MODE:
            super().wheelEvent(event)
            return

        delta = event.angleDelta().x() or event.angleDelta().y()
        self.scroll_x -= int(delta / 120 * 90)
        self._auto_follow = False
        self._clamp_scroll_x()
        self.update()
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.mode == self.SLIDE_MODE and self._auto_follow:
            self.scroll_x = self._max_scroll_x()
        else:
            self._clamp_scroll_x()

    def _toggle_mode(self) -> None:
        if self.mode == self.FIT_MODE:
            self.mode = self.SLIDE_MODE
            self._auto_follow = True
            self.scroll_x = self._max_scroll_x()
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.mode = self.FIT_MODE
            self.scroll_x = 0
            self._auto_follow = True
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()

    def _content_width(self) -> int:
        if self.mode == self.FIT_MODE:
            return max(1, self.width())
        return max(self.width(), int(self.total_time * self.SLIDE_PIXELS_PER_TIME_UNIT))

    def _time_to_x(self, time_value: float, content_width: int) -> int:
        if self.mode == self.FIT_MODE:
            return int((time_value / self.total_time) * content_width)
        return int(time_value * self.SLIDE_PIXELS_PER_TIME_UNIT)

    def _max_scroll_x(self) -> int:
        return max(0, self._content_width() - self.width())

    def _clamp_scroll_x(self) -> None:
        self.scroll_x = max(0, min(self.scroll_x, self._max_scroll_x()))

    def _paint_scrollbar(self, painter: QPainter, content_width: int, width: int, height: int) -> None:
        track_y = height - 7
        track_h = 3
        thumb_w = max(24, int((width / content_width) * width))
        max_scroll = max(1, content_width - width)
        thumb_x = int((self.scroll_x / max_scroll) * (width - thumb_w))

        painter.fillRect(0, track_y, width, track_h, QColor("#161b22"))
        painter.fillRect(thumb_x, track_y, thumb_w, track_h, QColor("#00d4ff"))


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

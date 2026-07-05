from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.domain.models import ProcessData


class SegmentAllocationSlider(QWidget):
    changed = Signal()

    MIN_SEGMENT_PERCENT = 10
    HANDLE_WIDTH = 8
    HANDLE_HEIGHT = 38

    def __init__(self, text: int = 30, data: int = 30, dynamic: int = 40):
        super().__init__()
        self._text_percent = text
        self._data_percent = data
        self._dynamic_percent = dynamic
        self._active_handle: int | None = None
        self.setMinimumHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.SizeHorCursor)

    @property
    def text_percent(self) -> int:
        return self._text_percent

    @property
    def data_percent(self) -> int:
        return self._data_percent

    @property
    def dynamic_percent(self) -> int:
        return self._dynamic_percent

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = painter.font()
        font.setPointSize(max(1, font.pointSize() - 1))
        painter.setFont(font)

        bar = self._bar_rect()
        text_x = bar.left()
        data_x = self._x_for_percent(self._text_percent)
        dynamic_x = self._x_for_percent(self._text_percent + self._data_percent)

        self._paint_segment(
            painter, QRectF(text_x, bar.top(), data_x - text_x, bar.height()),
            QColor("#2f6f78"), "Text", self._text_percent
        )
        self._paint_segment(
            painter,
            QRectF(data_x, bar.top(), dynamic_x - data_x, bar.height()),
            QColor("#536f4f"), "Data", self._data_percent
        )
        self._paint_segment(
            painter,
            QRectF(dynamic_x, bar.top(), bar.right() - dynamic_x, bar.height()),
            QColor("#5e5575"), "Heap/Stack", self._dynamic_percent
        )

        self._paint_bar_border(painter, bar)
        self._paint_handle(painter, data_x, bar)
        self._paint_handle(painter, dynamic_x, bar)

    def mousePressEvent(self, event) -> None:
        self._active_handle = self._nearest_handle(event.position().x())
        self._move_active_handle(event.position().x())

    def mouseMoveEvent(self, event) -> None:
        if self._active_handle is not None:
            self._move_active_handle(event.position().x())

    def mouseReleaseEvent(self, _event) -> None:
        self._active_handle = None

    def _paint_segment(
        self, painter: QPainter, rect: QRectF, color: QColor, label: str,
        percent: int
    ) -> None:
        if rect.width() <= 0:
            return

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRect(rect)

        metrics = painter.fontMetrics()
        label_text = metrics.elidedText(
            label, Qt.TextElideMode.ElideRight, max(0, int(rect.width()) - 8)
        )
        percent_text = metrics.elidedText(
            f"{percent}%", Qt.TextElideMode.ElideRight, max(0, int(rect.width()) - 8)
        )
        painter.setPen(QColor("#f2f5f7"))
        painter.drawText(
            QRectF(rect.left(), rect.top() + 2, rect.width(), rect.height() / 2),
            Qt.AlignmentFlag.AlignCenter,
            label_text,
        )
        painter.drawText(
            QRectF(rect.left(), rect.center().y(), rect.width(), rect.height() / 2),
            Qt.AlignmentFlag.AlignCenter,
            percent_text,
        )

    def _paint_bar_border(self, painter: QPainter, bar: QRectF) -> None:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.drawRoundedRect(bar, 2, 2)

    def _paint_handle(self, painter: QPainter, x: float, bar: QRectF) -> None:
        painter.setPen(QPen(QColor("#d0d7de"), 1))
        painter.setBrush(QColor("#141b23"))
        painter.drawRoundedRect(
            QRectF(
                x - self.HANDLE_WIDTH / 2,
                bar.center().y() - self.HANDLE_HEIGHT / 2,
                self.HANDLE_WIDTH,
                self.HANDLE_HEIGHT,
            ),
            2,
            2,
        )

    def _bar_rect(self) -> QRectF:
        return QRectF(4, 4, max(1, self.width() - 8), 36)

    def _x_for_percent(self, percent: int) -> float:
        bar = self._bar_rect()
        return bar.left() + bar.width() * percent / 100.0

    def _percent_for_x(self, x: float) -> int:
        bar = self._bar_rect()
        ratio = (x - bar.left()) / bar.width()
        return round(max(0.0, min(1.0, ratio)) * 100)

    def _nearest_handle(self, x: float) -> int:
        first_handle = self._x_for_percent(self._text_percent)
        second_handle = self._x_for_percent(self._text_percent + self._data_percent)
        return 1 if abs(x - first_handle) <= abs(x - second_handle) else 2

    def _move_active_handle(self, x: float) -> None:
        percent = self._percent_for_x(x)
        first_cut = self._text_percent
        second_cut = self._text_percent + self._data_percent

        if self._active_handle == 1:
            first_cut = max(
                self.MIN_SEGMENT_PERCENT,
                min(percent, second_cut - self.MIN_SEGMENT_PERCENT),
            )
        elif self._active_handle == 2:
            second_cut = max(
                first_cut + self.MIN_SEGMENT_PERCENT,
                min(percent, 100 - self.MIN_SEGMENT_PERCENT),
            )
        else:
            return

        self._text_percent = first_cut
        self._data_percent = second_cut - first_cut
        self._dynamic_percent = 100 - second_cut
        self.changed.emit()
        self.update()


class Process_Input(QGroupBox):
    def __init__(self, alg: str = ""):
        super().__init__("INGRESAR PROCESO")
        self.alg = alg

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(self._input_area())
        layout.addWidget(self._button_area())
        layout.addWidget(self._speed_area())
        self.btn_clean = QPushButton("Limpiar todo")
        self.btn_clean.setObjectName("dangerButton")
        layout.addWidget(self.btn_clean)

    def _input_area(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setSpacing(6)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("P1, P2, ...")
        form.addRow("Nombre:", self.input_name)

        self.input_cpu = QDoubleSpinBox()
        self.input_cpu.setRange(1.0, 9999.0)
        self.input_cpu.setDecimals(1)
        self.input_cpu.setValue(10.0)
        self.input_cpu.setSuffix(" u.t.")
        form.addRow("CPU Burst:", self.input_cpu)

        self.input_memory = QSpinBox()
        self.input_memory.setRange(4, 896)
        self.input_memory.setSingleStep(4)
        self.input_memory.setValue(64)
        self.input_memory.setSuffix(" MB")
        form.addRow("Memoria:", self.input_memory)
        segment_label = QLabel("Segmentos:")
        segment_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form.addRow(segment_label, self._segments_area())

        self.input_arrival = QDoubleSpinBox()
        self.input_arrival.setRange(0.0, 9999.0)
        self.input_arrival.setDecimals(1)
        self.input_arrival.setValue(0.0)
        self.input_arrival.setSuffix(" u.t.")
        form.addRow("Llegada:", self.input_arrival)

        if self.alg == "pr":
            self.input_priority = QSpinBox()
            self.input_priority.setRange(0, 5)
            self.input_priority.setValue(3)
            form.addRow("Prioridad:", self.input_priority)

        return widget

    def _segments_area(self) -> QWidget:
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.segment_slider = SegmentAllocationSlider()
        layout.addWidget(self.segment_slider)
        return widget

    def _button_area(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top = QHBoxLayout()
        self.btn_add = QPushButton("Agregar proceso")
        self.btn_add.setObjectName("primaryButton")
        self.btn_random = QPushButton("Aleatorio")
        self.input_random_count = QSpinBox()
        self.input_random_count.setRange(1, 20)
        self.input_random_count.setValue(5)
        self.input_random_count.setFixedWidth(64)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_random)
        top.addWidget(self.input_random_count)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        self.btn_start = QPushButton("Iniciar simulación")
        self.btn_start.setObjectName("successButton")
        self.btn_stop = QPushButton("Pausar")
        self.btn_kill = QPushButton("Detener")
        self.btn_kill.setObjectName("dangerButton")
        bottom.addWidget(self.btn_start, 1)
        bottom.addWidget(self.btn_stop)
        bottom.addWidget(self.btn_kill)
        layout.addLayout(bottom)
        return widget

    def _speed_area(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Velocidad:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(1, 20)
        self.slider_speed.setValue(5)
        self.value_speed = QLabel("5x")
        self.value_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_speed.setStyleSheet("color: #00d4ff; min-width: 30px;")
        layout.addWidget(label)
        layout.addWidget(self.slider_speed, 1)
        layout.addWidget(self.value_speed)
        return widget

    def get_process_data(self) -> ProcessData:
        process_data = ProcessData(
            name=self.input_name.text(),
            cpu_burst=self.input_cpu.value(),
            memory=self.input_memory.value() * 1024,
            arrival_time=self.input_arrival.value(),
            text_percent=self.segment_slider.text_percent,
            data_percent=self.segment_slider.data_percent,
            dynamic_percent=self.segment_slider.dynamic_percent,
        )
        if self.alg == "pr":
            process_data.priority = self.input_priority.value()
        return process_data

    def clear_name(self) -> None:
        self.input_name.clear()

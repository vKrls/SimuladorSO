"""
FCFS Process Scheduling Simulator
Simulador de Planificación de Procesos - Algoritmo FCFS (First Come First Served)
Gestión de Procesos y Memoria
"""

import sys
import random
import time
from dataclasses import dataclass, field
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QFrame, QScrollArea,
    QSplitter, QGroupBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QSizePolicy, QGraphicsDropShadowEffect, QMessageBox, QSlider,
    QTabWidget, QFormLayout
)
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, QPropertyAnimation, QEasingCurve,
    QRect, QSize, QPoint, QObject
)
from PySide6.QtGui import (
    QColor, QPalette, QFont, QFontDatabase, QPainter, QPen, QBrush,
    QLinearGradient, QPainterPath, QPixmap, QIcon, QIntValidator,
    QDoubleValidator
)

# resize
# ─────────────────────────────────────────────
#  DATOS / MODELOS
# ─────────────────────────────────────────────

@dataclass
class PCB:
    """Process Control Block"""
    pid: int
    name: str
    state: str = "NEW"          # NEW, READY, RUNNING, BLOCKED, TERMINATED
    burst_time: float = 0.0     # CPU burst time (ms)
    memory_required: int = 0    # KB
    arrival_time: float = 0.0
    start_time: float = -1.0
    finish_time: float = -1.0
    waiting_time: float = 0.0
    turnaround_time: float = 0.0
    remaining_time: float = 0.0
    progress: float = 0.0       # 0-100
    priority: int = 0
    program_counter: int = 0
    memory_base: int = 0        # Dirección base en memoria
    interrupts: int = 0
    color: str = "#00d4ff"

    @property
    def response_time(self):
        if self.start_time >= 0:
            return self.start_time - self.arrival_time
        return -1


PROCESS_COLORS = [
    "#00d4ff", "#ff6b35", "#7bc67e", "#f7c59f",
    "#c77dff", "#ff4d6d", "#48cae4", "#f4a261",
    "#06d6a0", "#ffd60a", "#e07a5f", "#81b29a",
]

STATE_COLORS = {
    "NEW":        "#546e7a",
    "READY":      "#1565c0",
    "RUNNING":    "#2e7d32",
    "BLOCKED":    "#e65100",
    "TERMINATED": "#424242",
}

STATE_LABELS = {
    "NEW":        "NUEVO",
    "READY":      "LISTO",
    "RUNNING":    "EJECUTANDO",
    "BLOCKED":    "BLOQUEADO",
    "TERMINATED": "TERMINADO",
}


# ─────────────────────────────────────────────
#  LÓGICA DEL SIMULADOR (hilo separado)
# ─────────────────────────────────────────────

class FCFSEngine(QObject):
    process_state_changed = Signal(int, str)      # pid, new_state
    process_progress = Signal(int, float)         # pid, progress %
    tick = Signal(float, int)                     # current_time, running_pid
    simulation_done = Signal(list)                # lista de PCBs finalizados
    log_event = Signal(str, str)                  # message, level
    gantt_update = Signal(int, float, float)      # pid, start, duration

    def __init__(self, processes: list, speed: float = 1.0):
        super().__init__()
        self.processes = [p for p in processes]
        self.speed = speed          # unidades por segundo
        self._running = True
        self._paused = False

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def run(self):
        """Ejecuta el algoritmo FCFS."""
        queue = sorted(self.processes, key=lambda p: p.arrival_time)
        current_time = 0.0
        finished = []

        self.log_event.emit("▶  Simulación FCFS iniciada", "INFO")
        self.log_event.emit(f"   {len(queue)} proceso(s) en cola", "INFO")

        # Poner todos en READY al inicio
        for p in queue:
            p.state = "READY"
            p.remaining_time = p.burst_time
            self.process_state_changed.emit(p.pid, "READY")

        for p in queue:
            if not self._running:
                break

            # Esperar si el proceso no ha llegado aún
            if current_time < p.arrival_time:
                gap = p.arrival_time - current_time
                self.log_event.emit(
                    f"   CPU inactiva por {gap:.1f} u.t. (esperando {p.name})", "WARN"
                )
                self._sleep(gap)
                current_time = p.arrival_time

            # Asignar CPU
            p.start_time = current_time
            p.state = "RUNNING"
            p.program_counter = p.memory_base
            self.process_state_changed.emit(p.pid, "RUNNING")
            self.log_event.emit(
                f"▶  {p.name} [PID {p.pid}] iniciado en t={current_time:.1f}", "RUN"
            )
            self.gantt_update.emit(p.pid, current_time, p.burst_time)

            # Simular ejecución con ticks cada 50ms reales
            elapsed = 0.0
            step = 0.1  # unidades de tiempo por tick
            while elapsed < p.burst_time and self._running:
                while self._paused and self._running:
                    time.sleep(0.05)

                # Interrupción aleatoria (5–20 por proceso, simplificado: 1 posible)
                chunk = min(step, p.burst_time - elapsed)
                elapsed += chunk
                p.remaining_time = max(0, p.burst_time - elapsed)
                p.progress = (elapsed / p.burst_time) * 100
                p.program_counter = p.memory_base + int(elapsed * 100)

                self.process_progress.emit(p.pid, p.progress)
                self.tick.emit(current_time + elapsed, p.pid)

                sleep_time = (step / self.speed) if self.speed > 0 else 0.1
                time.sleep(min(sleep_time, 0.2))

            if not self._running:
                break

            # Proceso finalizado
            current_time += p.burst_time
            p.finish_time = current_time
            p.turnaround_time = p.finish_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            p.state = "TERMINATED"
            p.progress = 100.0
            self.process_state_changed.emit(p.pid, "TERMINATED")
            self.log_event.emit(
                f"✔  {p.name} [PID {p.pid}] finalizado — "
                f"TAT={p.turnaround_time:.1f}  WT={p.waiting_time:.1f}", "DONE"
            )
            finished.append(p)

        if self._running:
            self.simulation_done.emit(finished)
            self.log_event.emit("■  Simulación completada", "INFO")

    def _sleep(self, units: float):
        secs = units / self.speed if self.speed > 0 else 0.05
        deadline = time.time() + min(secs, 10)
        while time.time() < deadline and self._running:
            time.sleep(0.05)


# ─────────────────────────────────────────────
#  WIDGETS PERSONALIZADOS
# ─────────────────────────────────────────────

class GlowLabel(QLabel):
    """Label con efecto glow."""
    def __init__(self, text, color="#00d4ff", font_size=14, bold=True, parent=None):
        super().__init__(text, parent)
        font = QFont("Courier New", font_size)
        font.setBold(bold)
        self.setFont(font)
        self.setStyleSheet(f"color: {color}; background: transparent;")
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(color))
        glow.setBlurRadius(18)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)


class StateChip(QLabel):
    """Badge de estado de proceso."""
    def __init__(self, state="NEW", parent=None):
        super().__init__(parent)
        self.set_state(state)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(110)
        font = QFont("Courier New", 8)
        font.setBold(True)
        self.setFont(font)

    def set_state(self, state: str):
        color = STATE_COLORS.get(state, "#546e7a")
        label = STATE_LABELS.get(state, state)
        self.setText(label)
        self.setStyleSheet(f"""
            background: {color}22;
            color: {color};
            border: 1px solid {color};
            border-radius: 8px;
            padding: 2px 6px;
        """)


class ProcessCard(QFrame):
    """Tarjeta visual de un proceso."""
    def __init__(self, pcb: PCB, parent=None):
        super().__init__(parent)
        self.pcb = pcb
        self._setup_ui()
        self.setFixedHeight(120)

    def _setup_ui(self):
        color = self.pcb.color
        self.setStyleSheet(f"""
            QFrame {{
                background: #0d1117;
                border: 1px solid {color}55;
                border-left: 3px solid {color};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Encabezado
        header = QHBoxLayout()
        name_lbl = QLabel(f"[PID {self.pcb.pid}] {self.pcb.name}")
        name_lbl.setStyleSheet(f"color: {color}; font-family: 'Courier New'; font-weight: bold; font-size: 11px;")
        header.addWidget(name_lbl)
        header.addStretch()
        self.state_chip = StateChip(self.pcb.state)
        header.addWidget(self.state_chip)
        layout.addLayout(header)

        # Info compacta
        info = QHBoxLayout()
        self.lbl_burst = QLabel(f"Burst: {self.pcb.burst_time:.0f} u.t.")
        self.lbl_mem = QLabel(f"Mem: {self.pcb.memory_required} KB")
        self.lbl_rem = QLabel(f"Rest: {self.pcb.remaining_time:.1f}")
        self.lbl_pc = QLabel(f"PC: {self.pcb.program_counter:#06x}")
        for lbl in [self.lbl_burst, self.lbl_mem, self.lbl_rem, self.lbl_pc]:
            lbl.setStyleSheet("color: #8b949e; font-family: 'Courier New'; font-size: 9px;")
            info.addWidget(lbl)
        info.addStretch()
        layout.addLayout(info)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: #161b22;
                border: none;
                border-radius: 4px;
                text-align: center;
                font-size: 0px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}99, stop:1 {color});
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Tiempos
        times = QHBoxLayout()
        self.lbl_wait = QLabel("Espera: —")
        self.lbl_tat = QLabel("TAT: —")
        self.lbl_resp = QLabel("Resp: —")
        for lbl in [self.lbl_wait, self.lbl_tat, self.lbl_resp]:
            lbl.setStyleSheet("color: #484f58; font-family: 'Courier New'; font-size: 9px;")
            times.addWidget(lbl)
        times.addStretch()
        layout.addLayout(times)

    def update_pcb(self, pcb: PCB):
        self.pcb = pcb
        self.state_chip.set_state(pcb.state)
        self.progress_bar.setValue(int(pcb.progress))
        self.lbl_rem.setText(f"Rest: {pcb.remaining_time:.1f}")
        self.lbl_pc.setText(f"PC: {pcb.program_counter:#06x}")
        if pcb.waiting_time > 0:
            self.lbl_wait.setText(f"Espera: {pcb.waiting_time:.1f}")
            self.lbl_wait.setStyleSheet("color: #f7c59f; font-family: 'Courier New'; font-size: 9px;")
        if pcb.turnaround_time > 0:
            self.lbl_tat.setText(f"TAT: {pcb.turnaround_time:.1f}")
            self.lbl_tat.setStyleSheet("color: #7bc67e; font-family: 'Courier New'; font-size: 9px;")
        if pcb.response_time >= 0:
            self.lbl_resp.setText(f"Resp: {pcb.response_time:.1f}")
            self.lbl_resp.setStyleSheet("color: #c77dff; font-family: 'Courier New'; font-size: 9px;")


class GanttWidget(QWidget):
    """Diagrama de Gantt interactivo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []   # (pid, name, color, start, duration)
        self.total_time = 1.0
        self.setMinimumHeight(70)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def add_segment(self, pid, name, color, start, duration):
        self.segments.append((pid, name, color, start, duration))
        self.total_time = max(self.total_time, start + duration)
        self.update()

    def clear(self):
        self.segments.clear()
        self.total_time = 1.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        bar_y = 20
        bar_h = 36
        label_y = bar_y + bar_h + 6

        # Fondo
        painter.fillRect(0, 0, w, h, QColor("#0d1117"))

        # Eje de tiempo
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.drawLine(0, bar_y + bar_h, w, bar_y + bar_h)

        if not self.segments:
            painter.setPen(QColor("#484f58"))
            painter.setFont(QFont("Courier New", 9))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, "[ Diagrama de Gantt ]")
            return

        for pid, name, color, start, duration in self.segments:
            x1 = int((start / self.total_time) * w)
            x2 = int(((start + duration) / self.total_time) * w)
            bw = max(x2 - x1, 2)

            # Bloque relleno con gradiente
            grad = QLinearGradient(x1, bar_y, x1, bar_y + bar_h)
            c = QColor(color)
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 200))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 80))
            painter.fillRect(x1, bar_y, bw, bar_h, grad)

            # Borde
            painter.setPen(QPen(QColor(color), 1))
            painter.drawRect(x1, bar_y, bw, bar_h)

            # Nombre (si hay espacio)
            if bw > 30:
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Courier New", 8, QFont.Bold))
                painter.drawText(x1 + 2, bar_y, bw - 4, bar_h,
                                 Qt.AlignCenter | Qt.TextWordWrap, name[:8])

            # Tick de tiempo inicial
            painter.setPen(QColor("#484f58"))
            painter.setFont(QFont("Courier New", 7))
            painter.drawText(x1, label_y, 40, 14, Qt.AlignLeft, f"{start:.0f}")

        # Tiempo final
        last = self.segments[-1]
        end_t = last[3] + last[4]
        end_x = int((end_t / self.total_time) * w) - 20
        painter.setPen(QColor("#484f58"))
        painter.setFont(QFont("Courier New", 7))
        painter.drawText(end_x, label_y, 40, 14, Qt.AlignRight, f"{end_t:.0f}")


class MemoryMapWidget(QWidget):
    """Mapa visual de memoria."""
    def __init__(self, total_kb=4096, parent=None):
        super().__init__(parent)
        self.total_kb = total_kb
        self.blocks = []   # (base_kb, size_kb, color, name)
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def allocate(self, base_kb, size_kb, color, name):
        self.blocks.append((base_kb, size_kb, color, name))
        self.update()

    def clear(self):
        self.blocks.clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar_h = 30
        bar_y = (h - bar_h) // 2

        painter.fillRect(0, 0, w, h, QColor("#0d1117"))

        # Fondo total de memoria (libre)
        painter.fillRect(0, bar_y, w, bar_h, QColor("#161b22"))
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.drawRect(0, bar_y, w - 1, bar_h)

        for base_kb, size_kb, color, name in self.blocks:
            x1 = int((base_kb / self.total_kb) * w)
            bw = max(int((size_kb / self.total_kb) * w), 2)
            c = QColor(color)
            grad = QLinearGradient(x1, bar_y, x1, bar_y + bar_h)
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 220))
            grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 100))
            painter.fillRect(x1 + 1, bar_y + 1, bw - 2, bar_h - 2, grad)
            if bw > 24:
                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Courier New", 7))
                painter.drawText(x1 + 2, bar_y, bw - 4, bar_h,
                                 Qt.AlignCenter, name[:6])

        # Etiqueta de total
        painter.setPen(QColor("#484f58"))
        painter.setFont(QFont("Courier New", 7))
        painter.drawText(0, bar_y + bar_h + 2, w, 14, Qt.AlignRight,
                         f"Total: {self.total_kb} KB")


# ─────────────────────────────────────────────
#  VENTANA PRINCIPAL
# ─────────────────────────────────────────────

class FCFSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FCFS Scheduler — Simulador de Gestión de Procesos")
        self.setMinimumSize(1200, 780)
        self.resize(1380, 860)

        self.processes: list[PCB] = []
        self.process_cards: dict[int, ProcessCard] = {}
        self.next_pid = 1
        self.color_idx = 0
        self.current_time = 0.0
        self.sim_thread: Optional[QThread] = None
        self.engine: Optional[FCFSEngine] = None
        self.sim_running = False
        self.memory_pointer = 256   # Dirección base inicial (KB)

        self._apply_theme()
        self._build_ui()

    # ── TEMA ──────────────────────────────────
    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Courier New';
            }
            QGroupBox {
                border: 1px solid #21262d;
                border-radius: 6px;
                margin-top: 16px;
                padding-top: 8px;
                font-family: 'Courier New';
                font-size: 10px;
                color: #484f58;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                color: #8b949e;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 4px;
                color: #c9d1d9;
                padding: 4px 8px;
                font-family: 'Courier New';
                font-size: 11px;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #00d4ff;
            }
            QPushButton {
                font-family: 'Courier New';
                font-size: 11px;
                border-radius: 4px;
                padding: 6px 14px;
            }
            QScrollBar:vertical {
                background: #161b22;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
            }
            QScrollBar:horizontal {
                background: #161b22;
                height: 8px;
            }
            QScrollBar::handle:horizontal {
                background: #30363d;
            }
            QTableWidget {
                background: #0d1117;
                border: 1px solid #21262d;
                gridline-color: #161b22;
                font-family: 'Courier New';
                font-size: 10px;
            }
            QTableWidget::item { padding: 4px 6px; }
            QTableWidget::item:selected { background: #1c2128; }
            QHeaderView::section {
                background: #161b22;
                color: #8b949e;
                border: none;
                border-bottom: 1px solid #30363d;
                padding: 4px 6px;
                font-family: 'Courier New';
                font-size: 10px;
            }
            QTextEdit {
                background: #161b22;
                border: 1px solid #21262d;
                color: #8b949e;
                font-family: 'Courier New';
                font-size: 10px;
            }
            QSlider::groove:horizontal {
                background: #21262d;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00d4ff;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #00d4ff55;
                border-radius: 2px;
            }
            QTabWidget::pane {
                border: 1px solid #21262d;
                background: #0d1117;
            }
            QTabBar::tab {
                background: #161b22;
                color: #8b949e;
                padding: 6px 14px;
                font-family: 'Courier New';
                font-size: 10px;
                border: 1px solid #21262d;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #0d1117;
                color: #00d4ff;
                border-color: #00d4ff55;
            }
        """)

    # ── BUILD UI ──────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Header
        root.addWidget(self._build_header())

        # Contenido principal (splitter horizontal)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background: #21262d; }")

        # Panel izquierdo: Input + Colas
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_layout.addWidget(self._build_input_panel())
        left_layout.addWidget(self._build_process_queue_panel())
        splitter.addWidget(left)

        # Panel derecho: Tabs (Ejecución, Estadísticas, PCB, Log)
        right_tabs = QTabWidget()
        right_tabs.addTab(self._build_execution_tab(), "▶  Ejecución")
        right_tabs.addTab(self._build_stats_tab(), "📊  Estadísticas")
        right_tabs.addTab(self._build_pcb_tab(), "🗃  PCB")
        right_tabs.addTab(self._build_log_tab(), "📋  Log")
        splitter.addWidget(right_tabs)

        splitter.setSizes([420, 880])
        root.addWidget(splitter, 1)

        # Barra inferior: CPU, tiempo, controles
        root.addWidget(self._build_bottom_bar())

    def _build_header(self):
        frame = QFrame()
        frame.setFixedHeight(52)
        frame.setStyleSheet("background: #161b22; border: 1px solid #21262d; border-radius: 6px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 0, 16, 0)

        title = GlowLabel("◈  FCFS SCHEDULER", "#00d4ff", 14)
        layout.addWidget(title)

        subtitle = QLabel("First Come First Served  |  Gestión de Procesos y Memoria")
        subtitle.setStyleSheet("color: #484f58; font-size: 10px;")
        layout.addWidget(subtitle)
        layout.addStretch()

        self.lbl_clock = GlowLabel("T: 0.0 u.t.", "#7bc67e", 11)
        layout.addWidget(self.lbl_clock)

        sep = QLabel("  |  ")
        sep.setStyleSheet("color: #21262d;")
        layout.addWidget(sep)

        self.lbl_status = QLabel("● INACTIVO")
        self.lbl_status.setStyleSheet("color: #484f58; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        return frame

    def _build_input_panel(self):
        group = QGroupBox("INGRESAR PROCESO")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(6)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("P1, P2, ...")
        self.inp_name.returnPressed.connect(self._add_process)
        form.addRow("Nombre:", self.inp_name)

        self.inp_burst = QDoubleSpinBox()
        self.inp_burst.setRange(1, 9999)
        self.inp_burst.setValue(10)
        self.inp_burst.setSuffix(" u.t.")
        self.inp_burst.setDecimals(1)
        form.addRow("CPU Burst:", self.inp_burst)

        self.inp_memory = QSpinBox()
        self.inp_memory.setRange(32, 8192)
        self.inp_memory.setValue(128)
        self.inp_memory.setSingleStep(32)
        self.inp_memory.setSuffix(" KB")
        form.addRow("Memoria:", self.inp_memory)

        self.inp_arrival = QDoubleSpinBox()
        self.inp_arrival.setRange(0, 9999)
        self.inp_arrival.setValue(0)
        self.inp_arrival.setSuffix(" u.t.")
        self.inp_arrival.setDecimals(1)
        form.addRow("Llegada:", self.inp_arrival)

        layout.addLayout(form)

        # Botones de acción
        btn_row1 = QHBoxLayout()
        self.btn_add = QPushButton("＋  Agregar Proceso")
        self.btn_add.setStyleSheet("""
            QPushButton { background: #1c2128; color: #00d4ff; border: 1px solid #00d4ff55; }
            QPushButton:hover { background: #00d4ff22; border-color: #00d4ff; }
            QPushButton:pressed { background: #00d4ff44; }
        """)
        self.btn_add.clicked.connect(self._add_process)
        btn_row1.addWidget(self.btn_add)

        self.btn_random = QPushButton("🎲  Aleatorio")
        self.btn_random.setStyleSheet("""
            QPushButton { background: #1c2128; color: #c77dff; border: 1px solid #c77dff55; }
            QPushButton:hover { background: #c77dff22; border-color: #c77dff; }
        """)
        self.btn_random.clicked.connect(self._add_random_processes)
        btn_row1.addWidget(self.btn_random)
        layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.btn_start = QPushButton("▶  Iniciar FCFS")
        self.btn_start.setStyleSheet("""
            QPushButton { background: #1a3a1a; color: #7bc67e; border: 1px solid #7bc67e66; font-weight: bold; }
            QPushButton:hover { background: #7bc67e22; border-color: #7bc67e; }
            QPushButton:disabled { background: #1c2128; color: #30363d; border-color: #21262d; }
        """)
        self.btn_start.clicked.connect(self._start_simulation)
        btn_row2.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedWidth(40)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setStyleSheet("""
            QPushButton { background: #1c2128; color: #f7c59f; border: 1px solid #f7c59f55; }
            QPushButton:hover { background: #f7c59f22; }
        """)
        self.btn_pause.clicked.connect(self._toggle_pause)
        btn_row2.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedWidth(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton { background: #1c2128; color: #ff4d6d; border: 1px solid #ff4d6d55; }
            QPushButton:hover { background: #ff4d6d22; }
        """)
        self.btn_stop.clicked.connect(self._stop_simulation)
        btn_row2.addWidget(self.btn_stop)
        layout.addLayout(btn_row2)

        # Velocidad
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidad:"))
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(1, 20)
        self.slider_speed.setValue(5)
        self.slider_speed.setFixedHeight(20)
        self.slider_speed.valueChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self.slider_speed)
        self.lbl_speed_val = QLabel("5×")
        self.lbl_speed_val.setStyleSheet("color: #00d4ff; min-width: 28px;")
        speed_layout.addWidget(self.lbl_speed_val)
        layout.addLayout(speed_layout)

        # Botón limpiar
        self.btn_clear = QPushButton("🗑  Limpiar Todo")
        self.btn_clear.setStyleSheet("""
            QPushButton { background: transparent; color: #484f58; border: 1px solid #21262d; }
            QPushButton:hover { color: #ff4d6d; border-color: #ff4d6d55; }
        """)
        self.btn_clear.clicked.connect(self._clear_all)
        layout.addWidget(self.btn_clear)

        return group

    def _build_process_queue_panel(self):
        group = QGroupBox("COLA DE PROCESOS (FCFS)")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        lbl = QLabel("Orden de ejecución (primero en llegar, primero atendido)")
        lbl.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(4)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

        # Contador de cola
        self.lbl_queue_count = QLabel("0 proceso(s) en cola")
        self.lbl_queue_count.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(self.lbl_queue_count)

        return group

    def _build_execution_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # CPU actual
        cpu_frame = QFrame()
        cpu_frame.setStyleSheet("background: #161b22; border: 1px solid #21262d; border-radius: 6px;")
        cpu_layout = QHBoxLayout(cpu_frame)
        cpu_layout.setContentsMargins(12, 8, 12, 8)

        cpu_lbl = GlowLabel("CPU", "#00d4ff", 10)
        cpu_layout.addWidget(cpu_lbl)

        sep = QLabel("│")
        sep.setStyleSheet("color: #21262d;")
        cpu_layout.addWidget(sep)

        self.lbl_cpu_process = QLabel("— INACTIVO —")
        self.lbl_cpu_process.setStyleSheet("color: #484f58; font-family: 'Courier New'; font-size: 11px;")
        cpu_layout.addWidget(self.lbl_cpu_process)
        cpu_layout.addStretch()

        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)
        self.cpu_progress.setFixedWidth(200)
        self.cpu_progress.setFixedHeight(10)
        self.cpu_progress.setTextVisible(False)
        self.cpu_progress.setStyleSheet("""
            QProgressBar { background: #0d1117; border: none; border-radius: 5px; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff66, stop:1 #00d4ff);
                border-radius: 5px;
            }
        """)
        cpu_layout.addWidget(self.cpu_progress)
        layout.addWidget(cpu_frame)

        # Gantt
        gantt_group = QGroupBox("DIAGRAMA DE GANTT")
        gantt_layout = QVBoxLayout(gantt_group)
        gantt_layout.setContentsMargins(6, 10, 6, 6)
        self.gantt = GanttWidget()
        gantt_layout.addWidget(self.gantt)
        layout.addWidget(gantt_group)

        # Mapa de memoria
        mem_group = QGroupBox("MAPA DE MEMORIA  (4096 KB total)")
        mem_layout = QVBoxLayout(mem_group)
        mem_layout.setContentsMargins(6, 10, 6, 6)
        self.memory_map = MemoryMapWidget(4096)
        mem_layout.addWidget(self.memory_map)
        layout.addWidget(mem_group)

        # Estado de colas
        queues_group = QGroupBox("ESTADO DE COLAS")
        queues_layout = QGridLayout(queues_group)
        queues_layout.setSpacing(6)

        labels = [("TOTAL", "#8b949e"), ("LISTOS", "#1565c0"),
                  ("EJECUTANDO", "#2e7d32"), ("BLOQUEADOS", "#e65100"), ("TERMINADOS", "#424242")]
        self.queue_counters = {}
        for i, (lbl, color) in enumerate(labels):
            box = QFrame()
            box.setStyleSheet(f"background: {color}22; border: 1px solid {color}55; border-radius: 4px;")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(8, 4, 8, 4)
            count = QLabel("0")
            count.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
            count.setAlignment(Qt.AlignCenter)
            name = QLabel(lbl)
            name.setStyleSheet("color: #484f58; font-size: 8px;")
            name.setAlignment(Qt.AlignCenter)
            box_layout.addWidget(count)
            box_layout.addWidget(name)
            queues_layout.addWidget(box, 0, i)
            self.queue_counters[lbl] = count
        layout.addWidget(queues_group)

        layout.addStretch()
        return widget

    def _build_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Métricas resumen
        metrics_group = QGroupBox("MÉTRICAS GLOBALES")
        metrics_layout = QGridLayout(metrics_group)
        metrics_layout.setSpacing(8)

        self.metric_labels = {}
        metrics = [
            ("avg_waiting",    "Espera Promedio",      "#f7c59f"),
            ("avg_turnaround", "TAT Promedio",         "#7bc67e"),
            ("avg_response",   "Respuesta Promedio",   "#c77dff"),
            ("throughput",     "Throughput",           "#00d4ff"),
            ("cpu_util",       "Utilización CPU",      "#ff6b35"),
            ("total_time",     "Tiempo Total",         "#48cae4"),
        ]
        for i, (key, label, color) in enumerate(metrics):
            frame = QFrame()
            frame.setStyleSheet(f"background: {color}11; border: 1px solid {color}33; border-radius: 4px;")
            f_layout = QVBoxLayout(frame)
            f_layout.setContentsMargins(10, 6, 10, 6)
            val = QLabel("—")
            val.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold; font-family: 'Courier New';")
            val.setAlignment(Qt.AlignCenter)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #484f58; font-size: 8px;")
            lbl.setAlignment(Qt.AlignCenter)
            f_layout.addWidget(val)
            f_layout.addWidget(lbl)
            self.metric_labels[key] = val
            metrics_layout.addWidget(frame, i // 3, i % 3)
        layout.addWidget(metrics_group)

        # Tabla de resultados
        table_group = QGroupBox("TABLA DE RESULTADOS POR PROCESO")
        table_layout = QVBoxLayout(table_group)

        self.stats_table = QTableWidget()
        cols = ["PID", "Nombre", "Llegada", "Burst", "Inicio", "Fin",
                "Espera", "TAT", "Resp.", "Memoria"]
        self.stats_table.setColumnCount(len(cols))
        self.stats_table.setHorizontalHeaderLabels(cols)
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setStyleSheet("""
            QTableWidget { alternate-background-color: #161b22; }
        """)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_layout.addWidget(self.stats_table)
        layout.addWidget(table_group)

        return widget

    def _build_pcb_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        lbl = QLabel("Process Control Block — Campos definidos en memoria")
        lbl.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(lbl)

        self.pcb_table = QTableWidget()
        cols = [
            "PID", "Nombre", "Estado", "PC", "Base Mem.", "Burst",
            "Restante", "Llegada", "Inicio", "Fin", "Espera", "TAT",
            "Interrupciones", "Prioridad"
        ]
        self.pcb_table.setColumnCount(len(cols))
        self.pcb_table.setHorizontalHeaderLabels(cols)
        self.pcb_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.pcb_table.setAlternatingRowColors(True)
        self.pcb_table.setStyleSheet("QTableWidget { alternate-background-color: #161b22; }")
        self.pcb_table.verticalHeader().setVisible(False)
        self.pcb_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.pcb_table)

        return widget

    def _build_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        lbl = QLabel("REGISTRO DE EVENTOS DEL SISTEMA")
        lbl.setStyleSheet("color: #8b949e; font-size: 10px;")
        header.addWidget(lbl)
        header.addStretch()
        btn_clear_log = QPushButton("Limpiar")
        btn_clear_log.setFixedWidth(60)
        btn_clear_log.setStyleSheet("""
            QPushButton { background: transparent; color: #484f58; border: 1px solid #21262d;
                          padding: 2px 8px; font-size: 9px; }
            QPushButton:hover { color: #c9d1d9; }
        """)
        btn_clear_log.clicked.connect(lambda: self.log_view.clear())
        header.addWidget(btn_clear_log)
        layout.addLayout(header)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        return widget

    def _build_bottom_bar(self):
        frame = QFrame()
        frame.setFixedHeight(40)
        frame.setStyleSheet("background: #161b22; border: 1px solid #21262d; border-radius: 4px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(20)

        # Proceso actual en CPU
        layout.addWidget(QLabel("CPU →"))
        self.lbl_running_name = QLabel("—")
        self.lbl_running_name.setStyleSheet("color: #7bc67e; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.lbl_running_name)

        sep1 = QLabel("│")
        sep1.setStyleSheet("color: #21262d;")
        layout.addWidget(sep1)

        layout.addWidget(QLabel("Procesos:"))
        self.lbl_process_count = QLabel("0")
        self.lbl_process_count.setStyleSheet("color: #00d4ff;")
        layout.addWidget(self.lbl_process_count)

        sep2 = QLabel("│")
        sep2.setStyleSheet("color: #21262d;")
        layout.addWidget(sep2)

        layout.addWidget(QLabel("Terminados:"))
        self.lbl_done_count = QLabel("0")
        self.lbl_done_count.setStyleSheet("color: #7bc67e;")
        layout.addWidget(self.lbl_done_count)

        sep3 = QLabel("│")
        sep3.setStyleSheet("color: #21262d;")
        layout.addWidget(sep3)

        layout.addWidget(QLabel("Memoria libre:"))
        self.lbl_mem_free = QLabel("4096 KB")
        self.lbl_mem_free.setStyleSheet("color: #c77dff;")
        layout.addWidget(self.lbl_mem_free)

        layout.addStretch()

        layout.addWidget(QLabel("Política: "))
        alg_lbl = GlowLabel("FCFS  (Non-preemptive)", "#00d4ff", 9)
        layout.addWidget(alg_lbl)

        return frame

    # ── LÓGICA ────────────────────────────────

    def _next_color(self):
        c = PROCESS_COLORS[self.color_idx % len(PROCESS_COLORS)]
        self.color_idx += 1
        return c

    def _add_process(self):
        name = self.inp_name.text().strip()
        if not name:
            name = f"P{self.next_pid}"

        burst = self.inp_burst.value()
        mem = self.inp_memory.value()
        arrival = self.inp_arrival.value()
        color = self._next_color()

        pcb = PCB(
            pid=self.next_pid,
            name=name,
            burst_time=burst,
            memory_required=mem,
            arrival_time=arrival,
            remaining_time=burst,
            color=color,
            memory_base=self.memory_pointer,
            interrupts=random.randint(5, 20),
        )
        self.next_pid += 1
        self.memory_pointer = (self.memory_pointer + mem) % 3800 + 128

        self.processes.append(pcb)
        self._add_card(pcb)
        self._update_pcb_table()
        self._update_queue_counters()

        self.inp_name.clear()
        self.inp_burst.setValue(random.randint(5, 40))
        self.inp_memory.setValue(random.choice([64, 128, 256, 512]))
        self.inp_arrival.setValue(arrival + random.uniform(0, 3))

        self._append_log(f"+ Proceso {pcb.name} [PID {pcb.pid}] añadido — "
                         f"Burst={burst:.1f}  Mem={mem}KB  Llegada={arrival:.1f}", "INFO")

    def _add_random_processes(self):
        names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon",
                 "Zeta", "Eta", "Theta", "Iota", "Kappa"]
        arrival = self.inp_arrival.value()
        for i in range(5):
            self.inp_name.setText(names[i % len(names)] + str(self.next_pid))
            self.inp_burst.setValue(round(random.uniform(5, 50), 1))
            self.inp_memory.setValue(random.choice([64, 128, 256, 512]))
            self.inp_arrival.setValue(round(arrival + i * random.uniform(0, 4), 1))
            self._add_process()

    def _add_card(self, pcb: PCB):
        card = ProcessCard(pcb)
        self.process_cards[pcb.pid] = card
        # Insertar antes del stretch
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self.lbl_queue_count.setText(f"{len(self.processes)} proceso(s) en cola")
        self.lbl_process_count.setText(str(len(self.processes)))

    def _update_queue_counters(self):
        counts = {"TOTAL": len(self.processes), "LISTOS": 0,
                  "EJECUTANDO": 0, "BLOQUEADOS": 0, "TERMINADOS": 0}
        for p in self.processes:
            if p.state == "READY":
                counts["LISTOS"] += 1
            elif p.state == "RUNNING":
                counts["EJECUTANDO"] += 1
            elif p.state == "BLOCKED":
                counts["BLOQUEADOS"] += 1
            elif p.state == "TERMINATED":
                counts["TERMINADOS"] += 1
        for key, lbl in self.queue_counters.items():
            lbl.setText(str(counts.get(key, 0)))
        self.lbl_done_count.setText(str(counts["TERMINADOS"]))

    def _update_pcb_table(self):
        self.pcb_table.setRowCount(len(self.processes))
        for row, p in enumerate(self.processes):
            vals = [
                str(p.pid), p.name, STATE_LABELS.get(p.state, p.state),
                f"{p.program_counter:#06x}", f"{p.memory_base} KB",
                f"{p.burst_time:.1f}", f"{p.remaining_time:.1f}",
                f"{p.arrival_time:.1f}",
                f"{p.start_time:.1f}" if p.start_time >= 0 else "—",
                f"{p.finish_time:.1f}" if p.finish_time >= 0 else "—",
                f"{p.waiting_time:.1f}" if p.waiting_time > 0 else "—",
                f"{p.turnaround_time:.1f}" if p.turnaround_time > 0 else "—",
                str(p.interrupts), str(p.priority)
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(p.color) if col == 1 else QColor("#c9d1d9"))
                if col == 2:
                    item.setForeground(QColor(STATE_COLORS.get(p.state, "#c9d1d9")))
                self.pcb_table.setItem(row, col, item)

    def _start_simulation(self):
        if not self.processes:
            QMessageBox.warning(self, "Sin procesos",
                                "Agregue al menos un proceso antes de iniciar.")
            return
        if self.sim_running:
            return

        self.sim_running = True
        self.gantt.clear()
        self.memory_map.clear()

        # Re-alocar memoria en el mapa visual
        base = 256
        for p in self.processes:
            self.memory_map.allocate(base, p.memory_required, p.color, p.name)
            base = (base + p.memory_required) % 3800 + 128

        speed = self.slider_speed.value()
        self.engine = FCFSEngine(self.processes, speed=speed)
        self.engine.process_state_changed.connect(self._on_state_changed)
        self.engine.process_progress.connect(self._on_progress)
        self.engine.tick.connect(self._on_tick)
        self.engine.simulation_done.connect(self._on_simulation_done)
        self.engine.log_event.connect(self._append_log)
        self.engine.gantt_update.connect(self._on_gantt_update)

        self.sim_thread = QThread()
        self.engine.moveToThread(self.sim_thread)
        self.sim_thread.started.connect(self.engine.run)
        self.sim_thread.start()

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_add.setEnabled(False)
        self.btn_random.setEnabled(False)

        self.lbl_status.setText("● EJECUTANDO")
        self.lbl_status.setStyleSheet("color: #7bc67e; font-size: 10px; font-weight: bold;")

    def _toggle_pause(self):
        if not self.engine:
            return
        if self.engine._paused:
            self.engine.resume()
            self.btn_pause.setText("⏸")
            self.lbl_status.setText("● EJECUTANDO")
            self.lbl_status.setStyleSheet("color: #7bc67e; font-size: 10px; font-weight: bold;")
        else:
            self.engine.pause()
            self.btn_pause.setText("▶")
            self.lbl_status.setText("● EN PAUSA")
            self.lbl_status.setStyleSheet("color: #f7c59f; font-size: 10px; font-weight: bold;")

    def _stop_simulation(self):
        if self.engine:
            self.engine.stop()
        if self.sim_thread:
            self.sim_thread.quit()
            self.sim_thread.wait(2000)
        self.sim_running = False
        self._reset_controls()
        self.lbl_status.setText("● DETENIDO")
        self.lbl_status.setStyleSheet("color: #ff4d6d; font-size: 10px; font-weight: bold;")
        self._append_log("■  Simulación detenida por el usuario", "WARN")

    def _reset_controls(self):
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸")
        self.btn_stop.setEnabled(False)
        self.btn_add.setEnabled(True)
        self.btn_random.setEnabled(True)

    def _clear_all(self):
        if self.sim_running:
            self._stop_simulation()
        self.processes.clear()
        self.process_cards.clear()
        self.next_pid = 1
        self.color_idx = 0
        self.memory_pointer = 256
        self.current_time = 0.0

        # Limpiar layout de tarjetas
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.gantt.clear()
        self.memory_map.clear()
        self.pcb_table.setRowCount(0)
        self.stats_table.setRowCount(0)
        self._update_queue_counters()
        self.lbl_queue_count.setText("0 proceso(s) en cola")
        self.lbl_process_count.setText("0")
        self.lbl_clock.setText("T: 0.0 u.t.")
        self.lbl_cpu_process.setText("— INACTIVO —")
        self.cpu_progress.setValue(0)
        self.lbl_running_name.setText("—")
        for v in self.metric_labels.values():
            v.setText("—")
        self.lbl_status.setText("● INACTIVO")
        self.lbl_status.setStyleSheet("color: #484f58; font-size: 10px; font-weight: bold;")
        self._append_log("Sistema reiniciado", "INFO")

    def _on_speed_changed(self, val):
        self.lbl_speed_val.setText(f"{val}×")
        if self.engine:
            self.engine.speed = val

    # ── SLOTS DE SEÑALES DEL ENGINE ────────────

    def _on_state_changed(self, pid: int, state: str):
        p = next((x for x in self.processes if x.pid == pid), None)
        if not p:
            return
        p.state = state
        card = self.process_cards.get(pid)
        if card:
            card.update_pcb(p)
        self._update_queue_counters()
        self._update_pcb_table()

        if state == "RUNNING":
            self.lbl_cpu_process.setText(f"{p.name}  [PID {p.pid}]  Burst: {p.burst_time:.1f} u.t.")
            self.lbl_cpu_process.setStyleSheet("color: #7bc67e; font-family: 'Courier New'; font-size: 11px;")
            self.lbl_running_name.setText(p.name)
        elif state == "TERMINATED":
            self.lbl_cpu_process.setText("— INACTIVO —")
            self.lbl_cpu_process.setStyleSheet("color: #484f58; font-family: 'Courier New'; font-size: 11px;")
            self.lbl_running_name.setText("—")
            self.cpu_progress.setValue(0)
            card = self.process_cards.get(pid)
            if card:
                card.setStyleSheet(card.styleSheet().replace("#0d1117", "#161b22"))

    def _on_progress(self, pid: int, progress: float):
        p = next((x for x in self.processes if x.pid == pid), None)
        if not p:
            return
        p.progress = progress
        card = self.process_cards.get(pid)
        if card:
            card.update_pcb(p)
        if p.state == "RUNNING":
            self.cpu_progress.setValue(int(progress))

    def _on_tick(self, t: float, pid: int):
        self.current_time = t
        self.lbl_clock.setText(f"T: {t:.1f} u.t.")

    def _on_gantt_update(self, pid: int, start: float, duration: float):
        p = next((x for x in self.processes if x.pid == pid), None)
        if p:
            self.gantt.add_segment(pid, p.name, p.color, start, duration)

    def _on_simulation_done(self, finished: list):
        self.sim_running = False
        self._reset_controls()
        self.lbl_status.setText("● COMPLETADO")
        self.lbl_status.setStyleSheet("color: #00d4ff; font-size: 10px; font-weight: bold;")

        if not finished:
            return

        # Calcular métricas
        total_wt = sum(p.waiting_time for p in finished)
        total_tat = sum(p.turnaround_time for p in finished)
        total_resp = sum(p.response_time for p in finished if p.response_time >= 0)
        n = len(finished)
        total_time = max(p.finish_time for p in finished)
        total_burst = sum(p.burst_time for p in finished)
        cpu_util = (total_burst / total_time * 100) if total_time > 0 else 0

        self.metric_labels["avg_waiting"].setText(f"{total_wt / n:.2f}")
        self.metric_labels["avg_turnaround"].setText(f"{total_tat / n:.2f}")
        self.metric_labels["avg_response"].setText(f"{total_resp / n:.2f}")
        self.metric_labels["throughput"].setText(f"{n / total_time:.3f}")
        self.metric_labels["cpu_util"].setText(f"{cpu_util:.1f}%")
        self.metric_labels["total_time"].setText(f"{total_time:.1f}")

        # Tabla de resultados
        self.stats_table.setRowCount(n)
        for row, p in enumerate(finished):
            vals = [
                str(p.pid), p.name,
                f"{p.arrival_time:.1f}", f"{p.burst_time:.1f}",
                f"{p.start_time:.1f}", f"{p.finish_time:.1f}",
                f"{p.waiting_time:.1f}", f"{p.turnaround_time:.1f}",
                f"{p.response_time:.1f}", f"{p.memory_required} KB"
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 1:
                    item.setForeground(QColor(p.color))
                self.stats_table.setItem(row, col, item)

        self._append_log(
            f"✔  Todos los procesos completados. "
            f"Espera prom.={total_wt/n:.2f}  TAT prom.={total_tat/n:.2f}  "
            f"CPU util.={cpu_util:.1f}%", "DONE"
        )

    def _append_log(self, message: str, level: str = "INFO"):
        colors = {
            "INFO": "#8b949e",
            "RUN":  "#7bc67e",
            "DONE": "#00d4ff",
            "WARN": "#f7c59f",
            "ERR":  "#ff4d6d",
        }
        color = colors.get(level, "#8b949e")
        self.log_view.append(
            f'<span style="color:{color}; font-family: Courier New; font-size:10px;">'
            f'{message}</span>'
        )

    def closeEvent(self, event):
        if self.engine:
            self.engine.stop()
        if self.sim_thread:
            self.sim_thread.quit()
            self.sim_thread.wait(1000)
        event.accept()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("FCFS Scheduler")
    app.setStyle("Fusion")

    # Paleta oscura base para Fusion
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0d1117"))
    palette.setColor(QPalette.WindowText, QColor("#c9d1d9"))
    palette.setColor(QPalette.Base, QColor("#161b22"))
    palette.setColor(QPalette.AlternateBase, QColor("#1c2128"))
    palette.setColor(QPalette.Text, QColor("#c9d1d9"))
    palette.setColor(QPalette.Button, QColor("#21262d"))
    palette.setColor(QPalette.ButtonText, QColor("#c9d1d9"))
    palette.setColor(QPalette.Highlight, QColor("#00d4ff44"))
    palette.setColor(QPalette.HighlightedText, QColor("#00d4ff"))
    app.setPalette(palette)

    window = FCFSWindow()
    window.show()
    sys.exit(app.exec())
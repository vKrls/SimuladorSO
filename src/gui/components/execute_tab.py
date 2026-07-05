from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.components.visual_widgets import GanttWidget, GlowLabel, MemoryMapWidget, STATE_COLORS, STATE_LABELS
from gui.domain.models import SimulationResult, UiProcess


class Execute_Tab(QTabWidget):
    EXECUTION_TAB = 0
    STATS_TAB = 1
    PCB_TAB = 2
    SYSTEM_TAB = 3

    command_submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.metrics: dict[str, QLabel] = {}
        self.counters: dict[str, QLabel] = {}
        self.device_counters: dict[str, QLabel] = {}
        self._last_processes: list[UiProcess] = []
        self._last_system_processes: list[UiProcess] = []
        self._last_state: dict = {}

        self.addTab(self._build_execution_tab(), "Ejecución")
        self.addTab(self._build_stats_tab(), "Estadísticas")
        self.addTab(self._build_pcb_tab(), "PCB")
        self.addTab(self._build_system_tab(), "Procesos del SO")
        self.addTab(self._build_log_tab(), "Log")
        self.currentChanged.connect(self._refresh_current_tab)

    def _build_execution_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        cpu_frame = QFrame()
        cpu_frame.setObjectName("panel")
        cpu_layout = QHBoxLayout(cpu_frame)
        cpu_layout.setContentsMargins(12, 8, 12, 8)
        cpu_layout.setSpacing(10)

        cpu_layout.addWidget(GlowLabel("CPU", "#00d4ff", 10))
        sep = QLabel("|")
        sep.setStyleSheet("color: #21262d;")
        cpu_layout.addWidget(sep)

        self.cpu_process = QLabel("-- INACTIVO --")
        self.cpu_process.setStyleSheet("color: #484f58; font-size: 11px;")
        cpu_layout.addWidget(self.cpu_process, 1)

        self.status = QLabel("Listo")
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status.setStyleSheet("color: #8b949e; font-size: 10px;")
        cpu_layout.addWidget(self.status)

        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setValue(0)
        self.cpu_progress.setFixedWidth(190)
        self.cpu_progress.setFixedHeight(9)
        self.cpu_progress.setTextVisible(False)
        self.cpu_progress.setStyleSheet("""
            QProgressBar { background: #0d1117; border: none; border-radius: 4px; }
            QProgressBar::chunk { background: #00d4ff; border-radius: 4px; }
        """)
        cpu_layout.addWidget(self.cpu_progress)
        layout.addWidget(cpu_frame)

        gantt_group = QGroupBox("DIAGRAMA DE GANTT")
        gantt_layout = QVBoxLayout(gantt_group)
        gantt_layout.setContentsMargins(6, 10, 6, 6)
        self.gantt = GanttWidget()
        gantt_layout.addWidget(self.gantt)
        layout.addWidget(gantt_group)

        memory_group = QGroupBox("MAPA DE MEMORIA")
        memory_layout = QVBoxLayout(memory_group)
        memory_layout.setContentsMargins(6, 10, 6, 6)
        self.memory_map = MemoryMapWidget()
        memory_layout.addWidget(self.memory_map)
        layout.addWidget(memory_group)

        queue_group = QGroupBox("ESTADO DE COLAS")
        queue_layout = QGridLayout(queue_group)
        queue_layout.setSpacing(6)
        labels = [
            ("TOTAL", "#8b949e"),
            ("NUEVOS", "#546e7a"),
            ("LISTOS", "#1565c0"),
            ("EJECUTANDO", "#2e7d32"),
            ("BLOQUEADOS", "#e65100"),
            ("TERMINADOS", "#7bc67e"),
        ]
        for index, (label, color) in enumerate(labels):
            queue_layout.addWidget(self._counter_box(label, color), 0, index)
        layout.addWidget(queue_group)

        devices_group = QGroupBox("DISPOSITIVOS DE ENTRADA/SALIDA")
        devices_layout = QGridLayout(devices_group)
        devices_layout.setSpacing(6)
        for index, device in enumerate(
            ["KEYBOARD", "MOUSE", "DISK", "PRINTER", "NETWORK"]
        ):
            value = QLabel(f"{device}: 0")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value.setStyleSheet(
                "color: #48cae4; background: #48cae411; "
                "border: 1px solid #48cae433; border-radius: 4px; "
                "padding: 5px; font-size: 9px;"
            )
            self.device_counters[device] = value
            devices_layout.addWidget(value, 0, index)
        layout.addWidget(devices_group)
        layout.addStretch()
        return widget

    def _counter_box(self, label: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {color}16; border: 1px solid {color}44; border-radius: 4px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        value = QLabel("0")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        name = QLabel(label)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("color: #ffffff; font-size: 8px;")
        layout.addWidget(value)
        layout.addWidget(name)
        self.counters[label] = value
        return frame

    def _build_stats_tab(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("statsTab")
        widget.setStyleSheet("""
            QWidget#statsTab QLabel { color: #ffffff; }
            QWidget#statsTab QGroupBox { color: #ffffff; }
            QWidget#statsTab QGroupBox::title { color: #ffffff; }
            QWidget#statsTab QTableWidget { color: #ffffff; }
            QWidget#statsTab QHeaderView::section { color: #ffffff; }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        metrics_group = QGroupBox("MÉTRICAS GLOBALES")
        metrics_layout = QGridLayout(metrics_group)
        metrics_layout.setSpacing(8)
        metric_color = "#2563eb"
        metrics = [
            ("avg_ready_time", "Ready Promedio", metric_color),
            ("avg_turnaround", "TAT Promedio", metric_color),
            ("avg_response", "Respuesta Promedio", metric_color),
            ("throughput", "Throughput", metric_color),
            ("cpu_util", "Utilización CPU", metric_color),
            ("total_time", "Tiempo Total", metric_color),
            ("interrupts", "Interrupciones", metric_color),
            ("errors", "Errores", metric_color),
            ("swap_outs", "Swap-outs", metric_color),
            ("swap_ins", "Swap-ins", metric_color),
            ("context_switches", "Cambios Contexto", metric_color),
            ("context_switch_time", "Tiempo Contexto", metric_color),
        ]
        for index, (key, label, color) in enumerate(metrics):
            metrics_layout.addWidget(self._metric_box(key, label, color), index // 3, index % 3)
        layout.addWidget(metrics_group)

        table_group = QGroupBox("TABLA DE RESULTADOS POR PROCESO")
        table_layout = QVBoxLayout(table_group)
        self.stats_table = QTableWidget()
        headers = ["PID", "Nombre", "Llegada", "Burst", "Inicio", "Fin", "Ready", "TAT", "Resp.", "Memoria"]
        self._configure_table(self.stats_table, headers, stretch=True)
        table_layout.addWidget(self.stats_table)
        layout.addWidget(table_group, 1)
        return widget

    def _metric_box(self, key: str, label: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {color}11; border: 1px solid {color}33; border-radius: 4px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)
        value = QLabel("--")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        text = QLabel(label)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet("color: #ffffff; font-size: 8px;")
        layout.addWidget(value)
        layout.addWidget(text)
        self.metrics[key] = value
        return frame

    def _build_pcb_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        label = QLabel("Process Control Block")
        label.setStyleSheet("color: #8b949e; font-size: 10px;")
        layout.addWidget(label)

        self.pcb_table = QTableWidget()
        headers = [
            "PID", "Nombre", "Estado", "PC", "Puntero bloque", "Base", "Límite",
            "Memoria", "Residente", "Burst", "Restante", "CPU", "Ready",
            "Bloqueado", "Fuera de RAM", "Llegada", "Inicio", "Fin", "TAT", "Resp.",
            "Interrup.", "Planificadas", "Historial interrupciones", "Dispositivo",
            "I/O restante", "Cambios ctx", "Swaps", "Error",
            "Momento error", "Prioridad",
        ]
        self._configure_table(self.pcb_table, headers, stretch=False)
        layout.addWidget(self.pcb_table, 1)
        return widget

    def _build_system_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        label = QLabel(
            "Procesos residentes del sistema operativo simulado "
            "(PIDs 0–99 y 128 MB reservados)"
        )
        label.setStyleSheet("color: #8b949e; font-size: 10px;")
        layout.addWidget(label)

        self.system_table = QTableWidget()
        headers = [
            "PID", "Nombre", "Estado", "Dirección bloque", "Base", "Límite",
            "Memoria", "Bloques", "Residente",
        ]
        self._configure_table(self.system_table, headers, stretch=True)
        layout.addWidget(self.system_table, 1)
        return widget

    def _build_log_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        label = QLabel("REGISTRO DE EVENTOS")
        label.setStyleSheet("color: #8b949e; font-size: 10px;")
        header.addWidget(label)
        header.addStretch()
        button = QPushButton("Limpiar")
        button.setFixedWidth(80)
        button.clicked.connect(lambda: self.log_view.clear())
        header.addWidget(button)
        layout.addLayout(header)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        command_row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Comando C")
        self.command_input.returnPressed.connect(self._submit_command)
        self.btn_send_command = QPushButton("Enviar")
        self.btn_send_command.setObjectName("primaryButton")
        self.btn_send_command.setFixedWidth(86)
        self.btn_send_command.clicked.connect(self._submit_command)
        command_row.addWidget(self.command_input, 1)
        command_row.addWidget(self.btn_send_command)
        layout.addLayout(command_row)
        return widget

    def _submit_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return
        self.command_input.clear()
        self.command_submitted.emit(command)

    def _configure_table(self, table: QTableWidget, headers: list[str], *, stretch: bool) -> None:
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        mode = QHeaderView.ResizeMode.Stretch if stretch else QHeaderView.ResizeMode.ResizeToContents
        table.horizontalHeader().setSectionResizeMode(mode)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_processes(
        self,
        processes: list[UiProcess],
        system_processes: list[UiProcess] | None = None,
    ) -> None:
        self._last_processes = processes
        self._last_system_processes = system_processes or []
        self._last_state = {}
        self._refresh_current_tab()

    def set_system_processes(self, processes: list[UiProcess]) -> None:
        self.system_table.setUpdatesEnabled(False)
        try:
            self.system_table.setRowCount(len(processes))
            for row, process in enumerate(processes):
                values = [
                    process.pid,
                    process.name,
                    STATE_LABELS.get(process.state, process.state),
                    process.memory_block_address,
                    self._memory(process.memory_base),
                    self._memory(process.memory_limit),
                    self._memory(process.memory),
                    process.assigned_blocks,
                    "Sí" if process.resident else "No",
                ]
                self._set_row(self.system_table, row, values, process)
        finally:
            self.system_table.setUpdatesEnabled(True)

    def clear(self) -> None:
        self.gantt.clear()
        self.memory_map.clear()
        self._last_processes = []
        self._last_system_processes = []
        self._last_state = {}
        self.stats_table.setRowCount(0)
        self.pcb_table.setRowCount(0)
        self.system_table.setRowCount(0)
        self.cpu_process.setText("-- INACTIVO --")
        self.cpu_process.setStyleSheet("color: #484f58; font-size: 11px;")
        self.cpu_progress.setValue(0)
        for value in self.metrics.values():
            value.setText("--")
        for value in self.counters.values():
            value.setText("0")
        for device, value in self.device_counters.items():
            value.setText(f"{device}: 0")
        self.log_view.clear()
        self.status.setText("Listo")

    def set_bridge_result(
        self,
        result: SimulationResult,
        processes: list[UiProcess] | None = None,
        system_processes: list[UiProcess] | None = None,
    ) -> None:
        self.status.setText("Comandos enviados a C" if result.ok else "No se pudo comunicar con C")
        if processes is not None:
            self._last_processes = processes
            self._last_system_processes = system_processes or []
            self._last_state = {}
            self._refresh_current_tab()

        if result.stdout_lines:
            for line in result.stdout_lines:
                self._append_log(line, "INFO")
        if result.error:
            self._append_log(result.error, "ERR")

    def set_exchange(self, result: SimulationResult, processes: list[UiProcess] | None = None) -> None:
        self.log_view.clear()
        self.status.setText("Simulación completada" if result.ok else "Simulación detenida")

        gantt = self._last_event(result.events, "gantt")
        segments = gantt.get("segments", []) if gantt else []
        self.gantt.set_segments(segments)

        memory = self._last_event(result.events, "memory_map")
        if memory:
            self.memory_map.set_blocks(memory.get("blocks", []), memory.get("total_kb"))

        stats = self._last_event(result.events, "stats")
        if stats:
            self._fill_metrics(stats.get("summary", {}))

        if processes is not None:
            self._last_processes = processes
            self._last_state = {
                "gantt": gantt or {},
                "memory_map": memory or {},
                "stats": stats.get("summary", {}) if stats else {},
            }
            self._refresh_current_tab()

        log_events = [event for event in result.events if event.get("type") == "log"]
        if log_events:
            for event in log_events:
                self._append_log(str(event.get("message", "")), str(event.get("level", "INFO")))
        elif result.error:
            self._append_log(result.error, "WARN")

    def append_log(self, message: str, level: str = "INFO") -> None:
        self._append_log(message, level)

    def set_gantt_event(self, event: dict) -> None:
        self.gantt.set_segments(
            event.get("segments", []),
            event.get("current_time"),
        )

    def set_live_state(
        self,
        processes: list[UiProcess],
        system_processes: list[UiProcess],
        state: dict,
    ) -> None:
        snapshot = state.get("snapshot", {})
        self._last_processes = processes
        self._last_system_processes = system_processes
        self._last_state = state
        self._refresh_current_tab()

        simulator_state = int(snapshot.get("simulator_state", 1))
        if simulator_state == 0:
            self.status.setText("Simulación en ejecución")
        elif processes:
            self.status.setText("Procesos cargados en C")
        else:
            self.status.setText("C esperando procesos")

    def _refresh_current_tab(self, index: int | None = None) -> None:
        if index is None:
            index = self.currentIndex()

        processes = self._last_processes
        system_processes = self._last_system_processes
        state = self._last_state
        gantt = state.get("gantt", {})
        memory = state.get("memory_map", {})
        stats = state.get("stats", {})
        segments = gantt.get("segments", [])

        if index == self.EXECUTION_TAB:
            self.gantt.set_segments(segments, gantt.get("current_time"))
            self.memory_map.set_blocks(memory.get("blocks", []), memory.get("total_kb"))
            self._update_counters(processes)
            self._update_device_counters(processes)
            self._update_cpu_panel(
                processes,
                segments,
                self._running_process_from_state(processes, state),
            )
        elif index == self.STATS_TAB:
            if stats:
                self._fill_metrics(stats)
            self._fill_stats_table(processes)
        elif index == self.PCB_TAB:
            self._fill_pcb_table(processes)
        elif index == self.SYSTEM_TAB:
            self.set_system_processes(system_processes)

    def _running_process_from_state(
        self,
        processes: list[UiProcess],
        state: dict,
    ) -> UiProcess | None:
        running_data = state.get("running")
        if running_data is None:
            return None

        running_pid = int(running_data.get("pid", -1))
        return next(
            (process for process in processes if process.pid == running_pid),
            None,
        )

    def _fill_metrics(self, summary: dict) -> None:
        for key, label in self.metrics.items():
            value = float(summary.get(key, 0.0))
            if key == "cpu_util":
                label.setText(f"{value:.1f}%")
            elif key == "throughput":
                label.setText(f"{value:.3f}")
            elif key in {
                "interrupts",
                "errors",
                "swap_outs",
                "swap_ins",
                "context_switches",
            }:
                label.setText(str(int(value)))
            else:
                label.setText(f"{value:.2f}")

    def _fill_stats_table(self, processes: list[UiProcess]) -> None:
        self.stats_table.setUpdatesEnabled(False)
        try:
            self.stats_table.setRowCount(len(processes))
            for row, process in enumerate(processes):
                values = [
                    process.pid,
                    process.name,
                    self._fmt(process.arrival_time),
                    self._fmt(process.burst_time),
                    self._dash(process.start_time),
                    self._dash(process.finish_time),
                    self._fmt(process.ready_time),
                    self._fmt(process.turnaround_time),
                    self._dash(process.response_time),
                    self._memory(process.memory),
                ]
                self._set_row(self.stats_table, row, values, process)
        finally:
            self.stats_table.setUpdatesEnabled(True)

    def _fill_pcb_table(self, processes: list[UiProcess]) -> None:
        self.pcb_table.setUpdatesEnabled(False)
        try:
            self.pcb_table.setRowCount(len(processes))
            for row, process in enumerate(processes):
                values = [
                    process.pid,
                    process.name,
                    STATE_LABELS.get(process.state, process.state),
                    f"0x{process.program_counter:X}",
                    process.memory_block_address,
                    self._memory(process.memory_base),
                    self._memory(process.memory_limit),
                    self._memory(process.memory),
                    "Sí" if process.resident else "No",
                    self._fmt(process.burst_time),
                    self._fmt(process.remaining_time or 0),
                    self._fmt(process.cpu_time),
                    self._fmt(process.ready_time),
                    self._fmt(process.blocked_time),
                    self._fmt(process.nonresident_time),
                    self._fmt(process.arrival_time),
                    self._dash(process.start_time),
                    self._dash(process.finish_time),
                    self._fmt(process.turnaround_time),
                    self._dash(process.response_time),
                    process.interrupts,
                    process.planned_interrupts,
                    self._interrupt_history(process),
                    process.io_device,
                    self._fmt(process.io_remaining),
                    process.context_switches,
                    process.swap_count,
                    (
                        f"{process.error_code}: {process.error_description}"
                        if process.error_code
                        else "--"
                    ),
                    self._dash(process.error_time),
                    process.priority,
                ]
                self._set_row(self.pcb_table, row, values, process)
        finally:
            self.pcb_table.setUpdatesEnabled(True)

    def _set_row(self, table: QTableWidget, row: int, values: list, process: UiProcess) -> None:
        for column, value in enumerate(values):
            text = str(value)
            item = table.item(row, column)
            if item is None:
                item = QTableWidgetItem()
                table.setItem(row, column, item)
            if item.text() != text:
                item.setText(text)
            if table is self.stats_table:
                item.setForeground(QColor("#ffffff"))
            elif column == 1:
                item.setForeground(QColor(process.color))
            elif column == 2:
                item.setForeground(QColor(STATE_COLORS.get(process.state, "#c9d1d9")))

    def _update_counters(self, processes: list[UiProcess]) -> None:
        counts = {key: 0 for key in self.counters}
        counts["TOTAL"] = len(processes)
        for process in processes:
            if process.state == "NEW":
                counts["NUEVOS"] += 1
            elif process.state == "READY":
                counts["LISTOS"] += 1
            elif process.state == "RUNNING":
                counts["EJECUTANDO"] += 1
            elif process.state == "BLOCKED":
                counts["BLOQUEADOS"] += 1
            elif process.state == "TERMINATED":
                counts["TERMINADOS"] += 1
        for key, value in counts.items():
            self.counters[key].setText(str(value))

    def _update_device_counters(self, processes: list[UiProcess]) -> None:
        counts = {device: 0 for device in self.device_counters}
        for process in processes:
            if process.state == "BLOCKED":
                if process.io_device in counts:
                    counts[process.io_device] += 1
        for device, count in counts.items():
            self.device_counters[device].setText(f"{device}: {count}")

    def _update_cpu_panel(
        self,
        processes: list[UiProcess],
        segments: list[dict],
        running_process: UiProcess | None,
    ) -> None:
        if running_process is not None:
            self.cpu_process.setText(
                f"{running_process.name} [PID {running_process.pid}]  "
                f"Rest: {self._fmt(running_process.remaining_time)} u.t."
            )
            self.cpu_process.setStyleSheet("color: #7bc67e; font-size: 11px;")
            self.cpu_progress.setValue(int(max(0, min(100, running_process.progress))))
            return

        if not processes:
            self.cpu_process.setText("-- INACTIVO --")
            self.cpu_process.setStyleSheet("color: #484f58; font-size: 11px;")
            self.cpu_progress.setValue(0)
            return

        if segments:
            last = segments[-1]
            kind = str(last.get("kind", "PROCESS"))
            if kind == "IDLE":
                text = f"CPU inactiva desde t={float(last.get('start', 0)):.1f}"
            elif kind == "CONTEXT_SWITCH":
                text = f"Cambio de contexto en t={float(last.get('start', 0)):.1f}"
            else:
                text = (
                    f"Último: {last.get('name', '--')} "
                    f"[PID {last.get('pid', '-')}]  "
                    f"t={float(last.get('start', 0)):.1f}"
                )
            self.cpu_process.setText(text)
            self.cpu_process.setStyleSheet("color: #8b949e; font-size: 11px;")
            self.cpu_progress.setValue(0)
            return

        self.cpu_process.setText(f"{len(processes)} proceso(s) en cola")
        self.cpu_process.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.cpu_progress.setValue(0)

    def _append_log(self, message: str, level: str = "INFO") -> None:
        colors = {
            "INFO": "#8b949e",
            "RUN": "#7bc67e",
            "DONE": "#00d4ff",
            "WARN": "#f7c59f",
            "ERR": "#ff4d6d",
        }
        color = colors.get(level, "#8b949e")
        self.log_view.append(
            f'<span style="color:{color}; font-family: Courier New; font-size:10px;">{escape(message)}</span>'
        )

    def _last_event(self, events: list[dict], event_type: str) -> dict | None:
        for event in reversed(events):
            if event.get("type") == event_type:
                return event
        return None

    def _fmt(self, value: float | int | None) -> str:
        if value is None:
            return "--"
        return f"{float(value):.1f}"

    def _dash(self, value: float | int | None) -> str:
        if value is None:
            return "--"
        return self._fmt(value)

    def _memory(self, value_kb: int) -> str:
        if value_kb >= 1024 * 1024:
            return f"{value_kb / (1024 * 1024):.2f} GB"
        if value_kb >= 1024:
            return f"{value_kb / 1024:.1f} MB"
        return f"{value_kb} KB"

    def _interrupt_history(self, process: UiProcess) -> str:
        if not process.interrupt_history:
            return "--"
        return ", ".join(
            f"{event.get('type', '?')}@{float(event.get('time', 0.0)):.1f}"
            for event in process.interrupt_history
        )

from __future__ import annotations

import random

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from gui.components.center import Center
from gui.components.footer import Footer
from gui.components.header import Header
from gui.simulation_client import ProcessData, SimulationClient, SimulationResult, UiProcess
from gui.simulation_clock import TICK, timer_interval_ms

EPSILON = 1e-9


class AlgorithmWindow(QWidget):
    def __init__(
        self,
        main_window,
        client: SimulationClient,
        *,
        algorithm: str,
        title: str,
        description: str,
        footer_text: str,
        input_mode: str = "",
    ):
        super().__init__()
        self.main_window = main_window
        self.client = client
        self.algorithm = algorithm
        self.input_mode = input_mode
        self.footer_text = footer_text

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_simulation)
        self._paused = False
        self._result: SimulationResult | None = None
        self._segments: list[dict] = []
        self._final_by_pid: dict[int, dict] = {}
        self._current_time = 0.0
        self._end_time = 0.0
        self._logged_segments: set[int] = set()
        self._last_queue_refresh = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.header = self._header(title, description)
        self.center = self._center(title)
        self.footer = self._footer(footer_text)

        layout.addWidget(self.header)
        layout.addWidget(self.center, 1)
        layout.addWidget(self.footer)
        self._sync_summary(self.client.processes_for(self.algorithm))
        self._set_controls_running(False)

    def _header(self, title: str, description: str) -> Header:
        header = Header()
        header.title.setText(title)
        header.desc.setText(description)
        header.btn_back.clicked.connect(self.go_back)
        return header

    def _center(self, title: str) -> Center:
        center = Center(self.client, self.input_mode)
        process_input = center.process_input
        process_input.btn_add.clicked.connect(self.add_process)
        process_input.btn_random.clicked.connect(self.add_random_processes)
        process_input.btn_start.clicked.connect(self.start_simulation)
        process_input.btn_stop.clicked.connect(self.pause_simulation)
        process_input.btn_kill.clicked.connect(self.stop_simulation)
        process_input.btn_clean.clicked.connect(self.clear_processes)
        process_input.slider_speed.valueChanged.connect(self.update_speed_label)
        process_input.btn_start.setText(f"Iniciar {title}")

        processes = self.client.processes_for(self.algorithm)
        center.process_queue.set_processes(processes)
        center.execute_tab.set_processes(processes)
        center.execute_tab.set_status("Crea procesos y pulsa iniciar simulación.")
        return center

    def _footer(self, footer_text: str) -> Footer:
        footer = Footer()
        footer.algorithm.setText(footer_text)
        return footer

    def add_process(self) -> None:
        if self._timer.isActive() or self._paused:
            return
        process_data = self.center.process_input.get_process_data()
        self.client.add_process(self.algorithm, process_data)
        self.center.process_input.clear_name()
        self._refresh_process_views("Proceso agregado. Listo para simular.")
        self.header.set_state("LISTO", "#00d4ff")

    def add_random_processes(self) -> None:
        if self._timer.isActive() or self._paused:
            return
        for _ in range(5):
            self.client.add_process(self.algorithm, self._random_process_data())
        self._refresh_process_views("Procesos aleatorios agregados.")
        self.header.set_state("LISTO", "#00d4ff")

    def start_simulation(self) -> None:
        if self._timer.isActive():
            return

        processes = self.client.processes_for(self.algorithm)
        if not processes:
            self.center.execute_tab.set_status("Agrega al menos un proceso.")
            self.header.set_state("SIN PROCESOS", "#f7c59f")
            return

        self._result = self.client.run(self.algorithm, apply_events=False)
        self._segments = self._extract_segments(self._result)
        self._final_by_pid = self._extract_final_processes(self._result)
        self._current_time = 0.0
        self._end_time = self._extract_total_time(self._result)
        self._logged_segments.clear()
        self._last_queue_refresh = 0.0
        self._paused = False

        self._prepare_runtime_state(processes)
        visible_segments, running_process = self._render_current_time()
        self.center.execute_tab.prepare_simulation(self._result, processes, self._end_time)
        self.center.execute_tab.update_time_view(
            self._current_time,
            processes,
            visible_segments,
            running_process,
            self._end_time,
        )
        self.center.process_queue.set_processes(processes)
        self._sync_summary(processes)
        self._set_controls_running(True)
        self.header.set_state("EJECUTANDO", "#7bc67e")
        self._timer.start(timer_interval_ms(self.center.process_input.slider_speed.value()))

    def pause_simulation(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self._paused = True
            self.center.process_input.btn_stop.setText("Continuar")
            self.center.execute_tab.set_status(f"Pausa en T: {self._current_time:.1f} u.t.")
            self.header.set_state("PAUSA", "#f7c59f")
            return

        if self._paused:
            self._paused = False
            self.center.process_input.btn_stop.setText("Pausar")
            self.header.set_state("EJECUTANDO", "#7bc67e")
            self._timer.start(timer_interval_ms(self.center.process_input.slider_speed.value()))

    def stop_simulation(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self._paused = False
        self._result = None
        self._set_controls_running(False)
        self.center.process_input.btn_stop.setText("Pausar")
        self.center.execute_tab.set_status(f"Detenido en T: {self._current_time:.1f} u.t.")
        self.header.set_state("DETENIDO", "#ff4d6d")
        self.footer.cpu.setText("--")

    def clear_processes(self) -> None:
        self.stop_simulation()
        self.client.clear_processes(self.algorithm)
        self.center.process_queue.clear()
        self.center.execute_tab.clear()
        self.center.execute_tab.set_status("Interfaz limpia.")
        self.header.total_time.setText("T: 0.0 u.t.")
        self.header.set_state("INACTIVO", "#484f58")
        self._current_time = 0.0
        self._end_time = 0.0
        self._segments = []
        self._final_by_pid = {}
        self._sync_summary([])

    def update_speed_label(self, value: int) -> None:
        self.center.process_input.value_speed.setText(f"{value}x")
        if self._timer.isActive():
            self._timer.setInterval(timer_interval_ms(value))

    def go_back(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self.main_window.show_main_menu()

    def _advance_simulation(self) -> None:
        if self._result is None:
            self._timer.stop()
            return

        self._timer.setInterval(timer_interval_ms(self.center.process_input.slider_speed.value()))
        self._current_time = min(self._end_time, self._current_time + TICK)
        processes = self.client.processes_for(self.algorithm)
        visible_segments, running_process = self._render_current_time()
        self._append_segment_logs()

        self.center.execute_tab.update_time_view(
            self._current_time,
            processes,
            visible_segments,
            running_process,
            self._end_time,
        )
        if self._should_refresh_queue():
            self.center.process_queue.set_processes(processes)
            self._last_queue_refresh = self._current_time
        self._sync_summary(processes)

        if self._current_time >= self._end_time - EPSILON:
            self._finish_simulation()

    def _finish_simulation(self) -> None:
        if self._result is None:
            return
        self._timer.stop()
        self.client.apply_result(self.algorithm, self._result)
        processes = self.client.processes_for(self.algorithm)
        self.center.execute_tab.set_exchange(self._result, processes)
        self.center.process_queue.set_processes(processes)
        self._sync_summary(processes)
        self.header.set_state("COMPLETADO", "#7bc67e")
        self._set_controls_running(False)
        self.center.process_input.btn_stop.setText("Pausar")
        self._paused = False
        self._result = None

    def _should_refresh_queue(self) -> bool:
        return (
            self._current_time >= self._end_time - EPSILON
            or self._current_time - self._last_queue_refresh >= 0.5 - EPSILON
        )

    def _prepare_runtime_state(self, processes: list[UiProcess]) -> None:
        for process in processes:
            final = self._final_by_pid.get(process.pid, {})
            process.state = "NEW"
            process.remaining_time = process.burst_time
            process.progress = 0.0
            process.start_time = None
            process.finish_time = None
            process.waiting_time = 0.0
            process.turnaround_time = 0.0
            process.response_time = None
            process.interrupts = 0
            process.assigned_blocks = int(final.get("assigned_blocks", process.assigned_blocks))
            process.waste_kb = int(final.get("waste_kb", process.waste_kb))
            process.memory_base = int(final.get("memory_base", process.memory_base))
            process.memory_limit = int(final.get("memory_limit", process.memory_limit))
            process.program_counter = process.memory_base

    def _render_current_time(self) -> tuple[list[dict], UiProcess | None]:
        processes = self.client.processes_for(self.algorithm)
        running_segment = self._running_segment_at(self._current_time)
        visible_segments = self._visible_segments_at(self._current_time)
        running_pid = int(running_segment["pid"]) if running_segment else None
        executed_by_pid = self._executed_time_by_pid(self._current_time)
        started_segments_by_pid = self._started_segments_by_pid(self._current_time)
        running_process: UiProcess | None = None

        for process in processes:
            final = self._final_by_pid.get(process.pid, {})
            executed = min(process.burst_time, executed_by_pid.get(process.pid, 0.0))
            process.progress = 100.0 if process.burst_time <= EPSILON else min(100.0, (executed / process.burst_time) * 100.0)
            process.remaining_time = max(0.0, process.burst_time - executed)
            process.program_counter = process.memory_base + int(executed * 100)
            process.interrupts = max(0, started_segments_by_pid.get(process.pid, 0) - 1)

            final_start = final.get("start_time")
            final_finish = final.get("finish_time")
            if final_start is not None and self._current_time >= float(final_start) - EPSILON:
                process.start_time = float(final_start)
                process.response_time = float(final.get("response_time", 0.0))
            else:
                process.start_time = None
                process.response_time = None

            if self._current_time < process.arrival_time - EPSILON:
                process.state = "NEW"
                process.waiting_time = 0.0
                process.turnaround_time = 0.0
                process.finish_time = None
            elif final_finish is not None and self._current_time >= float(final_finish) - EPSILON:
                process.state = "TERMINATED"
                process.remaining_time = 0.0
                process.progress = 100.0
                process.finish_time = float(final_finish)
                process.waiting_time = float(final.get("waiting_time", 0.0))
                process.turnaround_time = float(final.get("turnaround_time", 0.0))
                process.response_time = float(final.get("response_time", 0.0))
                process.program_counter = int(final.get("program_counter", process.program_counter))
                process.interrupts = int(final.get("interrupts", process.interrupts))
            elif running_pid == process.pid:
                process.state = "RUNNING"
                process.finish_time = None
                process.waiting_time = max(0.0, self._current_time - process.arrival_time - executed)
                process.turnaround_time = max(0.0, self._current_time - process.arrival_time)
                running_process = process
            else:
                process.state = "READY"
                process.finish_time = None
                process.waiting_time = max(0.0, self._current_time - process.arrival_time - executed)
                process.turnaround_time = max(0.0, self._current_time - process.arrival_time)

        return visible_segments, running_process

    def _visible_segments_at(self, current_time: float) -> list[dict]:
        visible: list[dict] = []
        for segment in self._segments:
            start = float(segment.get("start", 0.0))
            duration = float(segment.get("duration", 0.0))
            end = start + duration
            if current_time <= start + EPSILON:
                continue
            shown = min(current_time, end) - start
            if shown <= EPSILON:
                continue
            partial = dict(segment)
            partial["duration"] = round(shown, 3)
            visible.append(partial)
        return visible

    def _running_segment_at(self, current_time: float) -> dict | None:
        for segment in self._segments:
            start = float(segment.get("start", 0.0))
            end = start + float(segment.get("duration", 0.0))
            if start - EPSILON <= current_time < end - EPSILON:
                return segment
        return None

    def _executed_time_by_pid(self, current_time: float) -> dict[int, float]:
        executed: dict[int, float] = {}
        for segment in self._segments:
            pid = int(segment.get("pid", 0))
            start = float(segment.get("start", 0.0))
            duration = float(segment.get("duration", 0.0))
            end = start + duration
            if current_time <= start + EPSILON:
                continue
            done = min(current_time, end) - start
            if done > EPSILON:
                executed[pid] = executed.get(pid, 0.0) + done
        return executed

    def _started_segments_by_pid(self, current_time: float) -> dict[int, int]:
        started: dict[int, int] = {}
        for segment in self._segments:
            start = float(segment.get("start", 0.0))
            if current_time >= start - EPSILON:
                pid = int(segment.get("pid", 0))
                started[pid] = started.get(pid, 0) + 1
        return started

    def _append_segment_logs(self) -> None:
        for index, segment in enumerate(self._segments):
            if index in self._logged_segments:
                continue
            start = float(segment.get("start", 0.0))
            if self._current_time >= start - EPSILON:
                self._logged_segments.add(index)
                self.center.execute_tab.append_log(
                    f"t={start:.1f}: {segment.get('name', '--')} entra a CPU por "
                    f"{float(segment.get('duration', 0.0)):.1f} u.t.",
                    "RUN",
                )

    def _extract_segments(self, result: SimulationResult) -> list[dict]:
        gantt = self._last_event(result.events, "gantt")
        return list(gantt.get("segments", [])) if gantt else []

    def _extract_final_processes(self, result: SimulationResult) -> dict[int, dict]:
        final: dict[int, dict] = {}
        for event in result.events:
            if event.get("type") == "process_update":
                final[int(event.get("pid", 0))] = event
        return final

    def _extract_total_time(self, result: SimulationResult) -> float:
        stats = self._last_event(result.events, "stats")
        if stats:
            return max(0.0, float(stats.get("summary", {}).get("total_time", 0.0)))
        if not self._segments:
            return 0.0
        return max(float(segment.get("start", 0.0)) + float(segment.get("duration", 0.0)) for segment in self._segments)

    def _last_event(self, events: list[dict], event_type: str) -> dict | None:
        for event in reversed(events):
            if event.get("type") == event_type:
                return event
        return None

    def _refresh_process_views(self, status: str) -> None:
        processes = self.client.processes_for(self.algorithm)
        self.center.process_queue.set_processes(processes)
        self.center.execute_tab.set_processes(processes)
        self.center.execute_tab.set_status(status)
        self._sync_summary(processes)

    def _sync_summary(self, processes: list[UiProcess]) -> None:
        total = len(processes)
        finished = sum(1 for process in processes if process.state == "TERMINATED")
        total_time = self._current_time if self._timer.isActive() or self._paused else max(
            [0.0] + [process.finish_time or 0.0 for process in processes]
        )
        used_memory = sum(process.memory for process in processes)
        free_memory = max(0, 4096 - used_memory)
        running = next((process for process in processes if process.state == "RUNNING"), None)

        self.header.total_time.setText(f"T: {total_time:.1f} u.t.")
        self.footer.process.setText(str(total))
        self.footer.finished.setText(str(finished))
        self.footer.memory.setText(f"{free_memory} KB")
        if running:
            self.footer.cpu.setText(running.name[:10])
        elif finished == total and total > 0:
            self.footer.cpu.setText("Completo")
        else:
            self.footer.cpu.setText("--")

    def _set_controls_running(self, running: bool) -> None:
        process_input = self.center.process_input
        process_input.btn_add.setEnabled(not running)
        process_input.btn_random.setEnabled(not running)
        process_input.btn_start.setEnabled(not running)
        process_input.btn_clean.setEnabled(not running)
        process_input.btn_stop.setEnabled(running)
        process_input.btn_kill.setEnabled(running)
        if not running:
            process_input.btn_stop.setText("Pausar")

    def _random_process_data(self) -> ProcessData:
        process_data = ProcessData(
            name="",
            cpu_burst=float(random.randint(1, 18)),
            memory=random.randint(1, 16) * 64,
            arrival_time=float(random.randint(0, 12)),
        )
        if self.input_mode == "rr":
            process_data.quantum = self.center.process_input.input_quantum.value()
        if self.input_mode == "pr":
            process_data.priority = random.randint(0, 9)
        return process_data

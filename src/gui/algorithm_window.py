from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget

from gui.components.center import Center
from gui.components.footer import Footer
from gui.components.header import Header
from gui.simulation_client import ProcessData, SimulationClient, UiProcess


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

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(120)
        self._poll_timer.timeout.connect(self._poll_c_output)
        self._paused = False
        self._simulation_started = False

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
        selected_index = header.memory_combo.findData(self.client.memory_algorithm)
        header.memory_combo.setCurrentIndex(max(0, selected_index))
        header.memory_combo.currentIndexChanged.connect(
            self.change_memory_algorithm
        )
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
        process_input.slider_speed.sliderReleased.connect(self.send_speed)
        algorithm_label = {
            "fcfs": "FCFS",
            "sjf_nonpreemptive": "SJF-N",
            "sjf_preemptive": "SJF-A",
            "round_robin": "Round Robin",
            "priority_nonpreemptive": "Prioridades-N",
            "priority_preemptive": "Prioridades-A",
        }.get(self.algorithm, title)
        process_input.btn_start.setText(f"Iniciar {algorithm_label}")

        processes = self.client.processes_for(self.algorithm)
        center.process_queue.set_processes(processes)
        center.execute_tab.set_processes(processes)
        center.execute_tab.set_status("Crea procesos y envíalos al programa en C.")
        return center

    def _footer(self, footer_text: str) -> Footer:
        footer = Footer()
        footer.algorithm.setText(
            f"{footer_text} | Memoria: {self.client.memory_algorithm_name}"
        )
        return footer

    def add_process(self) -> None:
        process_data = self.center.process_input.get_process_data()
        _, result = self.client.load_process(self.algorithm, process_data)
        self.center.process_input.clear_name()
        self.center.execute_tab.set_bridge_result(
            result,
            self.client.processes_for(self.algorithm),
        )
        if result.ok:
            self._poll_timer.start()
            if self._simulation_started:
                self._refresh_process_views("Proceso agregado durante la ejecución.")
                self.header.set_state(
                    "PAUSA" if self._paused else "C EJECUTANDO",
                    "#f7c59f" if self._paused else "#7bc67e",
                )
            else:
                self._refresh_process_views("Proceso cargado en C.")
                self.header.set_state("CARGADO", "#00d4ff")
        else:
            self.header.set_state("ERROR", "#ff4d6d")

    def add_random_processes(self) -> None:
        if self._simulation_started:
            return

        quantum = 0.0
        if self.input_mode == "rr":
            quantum = self.center.process_input.input_quantum.value()

        result = self.client.request_random_processes(self.algorithm, quantum)
        self.center.execute_tab.set_bridge_result(
            result,
            self.client.processes_for(self.algorithm),
        )
        if result.ok:
            self._poll_timer.start()
            self.center.execute_tab.set_status("Cargando 5 procesos aleatorios desde C...")
            self.header.set_state("CARGANDO", "#00d4ff")
        else:
            self.header.set_state("ERROR", "#ff4d6d")

    def start_simulation(self) -> None:
        processes = self.client.processes_for(self.algorithm)
        if not self.client.has_processes_for(self.algorithm):
            self.center.execute_tab.set_status("Agrega al menos un proceso.")
            self.header.set_state("SIN PROCESOS", "#f7c59f")
            return

        result = self.client.run(self.algorithm)
        self.center.execute_tab.set_bridge_result(result, processes)
        self.center.process_queue.set_processes(processes)
        self._sync_summary(processes)

        if result.ok:
            self._paused = False
            self._simulation_started = True
            self.center.process_input.btn_stop.setText("Pausar")
            self._set_controls_running(True)
            self._poll_timer.start()
            self.header.set_state("C EJECUTANDO", "#7bc67e")
        else:
            self.header.set_state("ERROR", "#ff4d6d")

    def pause_simulation(self) -> None:
        if self._paused:
            result = self.client.send_run()
            if result.ok:
                self._paused = False
                self.center.process_input.btn_stop.setText("Pausar")
                self.header.set_state("C EJECUTANDO", "#7bc67e")
        else:
            result = self.client.send_pause()
            if result.ok:
                self._paused = True
                self.center.process_input.btn_stop.setText("Continuar")
                self.header.set_state("PAUSA", "#f7c59f")
        self.center.execute_tab.set_bridge_result(result, self.client.processes_for(self.algorithm))

    def stop_simulation(self) -> None:
        result = self.client.stop()
        self._poll_c_output()
        self._poll_timer.stop()
        self.center.execute_tab.set_bridge_result(result, self.client.processes_for(self.algorithm))
        self._paused = False
        self._simulation_started = False
        self.center.process_input.btn_stop.setText("Pausar")
        self.header.set_state("DETENIDO", "#ff4d6d")
        self.footer.cpu.setText("--")
        self._set_controls_running(False)

    def clear_processes(self) -> None:
        if self.client.is_process_running():
            self.stop_simulation()
        self.client.clear_processes(self.algorithm)
        self.center.process_queue.clear()
        self.center.execute_tab.clear()
        self.center.execute_tab.set_status("Interfaz limpia.")
        self.header.total_time.setText("T: 0.0 u.t.")
        self.header.set_state("INACTIVO", "#484f58")
        self._sync_summary([])

    def update_speed_label(self, value: int) -> None:
        self.center.process_input.value_speed.setText(f"{value}x")

    def send_speed(self) -> None:
        speed = self.center.process_input.slider_speed.value()
        result = self.client.send_speed(self.algorithm, speed)
        if result.ok and self.client.is_process_running():
            self.center.execute_tab.append_log(
                f"Velocidad actualizada: {speed}x",
                "INFO",
            )

    def change_memory_algorithm(self, index: int) -> None:
        memory_algorithm = self.header.memory_combo.itemData(index)
        if memory_algorithm is None:
            return

        result = self.client.configure_memory_algorithm(
            self.algorithm,
            int(memory_algorithm),
        )
        self.footer.algorithm.setText(
            f"{self.footer_text} | Memoria: {self.client.memory_algorithm_name}"
        )

        if result.error:
            self.center.execute_tab.append_log(result.error, "ERR")
            self.header.set_state("ERROR", "#ff4d6d")
            return

        if result.payload.get("sent"):
            self.center.execute_tab.append_log(
                f"Política de memoria actualizada: "
                f"{self.client.memory_algorithm_name}. "
                "Se aplicará a las próximas asignaciones.",
                "INFO",
            )
        else:
            self.center.execute_tab.append_log(
                f"Política de memoria seleccionada: "
                f"{self.client.memory_algorithm_name}.",
                "INFO",
            )

    def go_back(self) -> None:
        self._poll_timer.stop()
        self.main_window.show_main_menu()

    def _poll_c_output(self) -> None:
        events = []
        for line in self.client.read_stdout_lines():
            event = self.client.parse_event(line, self.algorithm)
            if event is None:
                self.center.execute_tab.append_log(line, "INFO")
            else:
                events.append(event)

        if events:
            state = self.client.apply_events(self.algorithm, events)
            processes = self.client.processes_for(self.algorithm)
            self.center.process_queue.set_processes(processes)
            self.center.execute_tab.set_live_state(processes, state)
            self._sync_summary(processes, state)

            if not self._simulation_started:
                self.center.execute_tab.set_status("Procesos cargados en C.")
                self.header.set_state("CARGADO", "#00d4ff")

        for line in self.client.read_stderr_lines():
            self.center.execute_tab.append_log(line, "ERR")

        if not self.client.is_process_running():
            self._poll_timer.stop()
            if self.header.state.text() == "C EJECUTANDO":
                self.header.set_state("FINALIZADO", "#7bc67e")
                self._set_controls_running(False)
            self._simulation_started = False

    def _refresh_process_views(self, status: str) -> None:
        processes = self.client.processes_for(self.algorithm)
        self.center.process_queue.set_processes(processes)
        self.center.execute_tab.set_processes(processes)
        self.center.execute_tab.set_status(status)
        self._sync_summary(processes)

    def _sync_summary(
        self,
        processes: list[UiProcess],
        state: dict | None = None,
    ) -> None:
        total = len(processes) + self.client.random_process_count_for(self.algorithm)
        finished = sum(
            1 for process in processes
            if process.state in {"TERMINATED", "ERROR"}
        )
        state = state or self.client.latest_state(self.algorithm)
        snapshot = state.get("snapshot", {})
        memory = state.get("memory_map", {})
        free_memory = int(memory.get("free_kb", 4096))
        current_time = float(snapshot.get("current_time", 0.0))

        self.header.total_time.setText(f"T: {current_time:.1f} u.t.")
        self.footer.process.setText(str(total))
        self.footer.finished.setText(str(finished))
        self.footer.memory.setText(f"{free_memory} KB")
        self.footer.cpu.setText("C" if self.client.is_process_running() else "--")

    def _set_controls_running(self, running: bool) -> None:
        process_input = self.center.process_input
        process_input.btn_add.setEnabled(True)
        process_input.btn_random.setEnabled(not running)
        process_input.btn_start.setEnabled(not running)
        process_input.btn_clean.setEnabled(not running)
        process_input.btn_stop.setEnabled(running)
        process_input.btn_kill.setEnabled(running)

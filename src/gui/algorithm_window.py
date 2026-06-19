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
        process_input.btn_start.setText(f"Enviar a C ({title})")

        processes = self.client.processes_for(self.algorithm)
        center.process_queue.set_processes(processes)
        center.execute_tab.set_processes(processes)
        center.execute_tab.set_status("Crea procesos y envíalos al programa en C.")
        return center

    def _footer(self, footer_text: str) -> Footer:
        footer = Footer()
        footer.algorithm.setText(footer_text)
        return footer

    def add_process(self) -> None:
        if self.client.is_process_running():
            return
        process_data = self.center.process_input.get_process_data()
        self.client.add_process(self.algorithm, process_data)
        self.center.process_input.clear_name()
        self._refresh_process_views("Proceso agregado. Pendiente de enviar a C.")
        self.header.set_state("LISTO", "#00d4ff")

    def add_random_processes(self) -> None:
        if self.client.is_process_running():
            return

        quantum = 0.0
        if self.input_mode == "rr":
            quantum = self.center.process_input.input_quantum.value()

        self.client.request_random_processes(self.algorithm, quantum)
        self._refresh_process_views("RANDOM pendiente: C generará 5 procesos.")
        self.header.set_state("LISTO", "#00d4ff")

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

    def go_back(self) -> None:
        self._poll_timer.stop()
        self.main_window.show_main_menu()

    def _poll_c_output(self) -> None:
        for line in self.client.read_stdout_lines():
            self.center.execute_tab.append_log(line, "INFO")
        for line in self.client.read_stderr_lines():
            self.center.execute_tab.append_log(line, "ERR")

        if not self.client.is_process_running():
            self._poll_timer.stop()
            if self.header.state.text() == "C EJECUTANDO":
                self.header.set_state("FINALIZADO", "#7bc67e")
                self._set_controls_running(False)

    def _refresh_process_views(self, status: str) -> None:
        processes = self.client.processes_for(self.algorithm)
        self.center.process_queue.set_processes(processes)
        self.center.execute_tab.set_processes(processes)
        self.center.execute_tab.set_status(status)
        self._sync_summary(processes)

    def _sync_summary(self, processes: list[UiProcess]) -> None:
        total = len(processes) + self.client.random_process_count_for(self.algorithm)
        finished = sum(1 for process in processes if process.state == "TERMINATED")
        used_memory = sum(process.memory for process in processes)
        free_memory = max(0, 4096 - used_memory)

        self.header.total_time.setText("T: --")
        self.footer.process.setText(str(total))
        self.footer.finished.setText(str(finished))
        self.footer.memory.setText(f"{free_memory} KB")
        self.footer.cpu.setText("C" if self.client.is_process_running() else "--")

    def _set_controls_running(self, running: bool) -> None:
        process_input = self.center.process_input
        process_input.btn_add.setEnabled(not running)
        process_input.btn_random.setEnabled(not running)
        process_input.btn_start.setEnabled(not running)
        process_input.btn_clean.setEnabled(not running)
        process_input.btn_stop.setEnabled(running)
        process_input.btn_kill.setEnabled(running)

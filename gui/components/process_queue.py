from PySide6.QtWidgets import QProgressBar, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget, QFrame, QLabel

from models.pcb import Pcb

label_style = """
    font-size: 10px;
    color: gray;
"""

frame_style = """
QFrame#infoFrame {
    background-color: rgba(33, 150, 243, 0.13);
    border: 1px solid rgba(33, 150, 243, 0.35);
    border-radius: 4px;
}

QFrame#infoFrame QLabel {
    color: #BBDEFB;
    font-size: 12px;
    border: none;
    background: transparent;
    padding: 0px;
    margin: 0px;
}
"""

class Process_Queue(QFrame):
    def __init__(self, alg: str = ""):
        super().__init__()
        self.alg = alg

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.setSpacing(2)

        layout.addWidget(self._header())
        layout.addWidget(self._process_queue())
        layout.addWidget(self._footer())
    

    def _header(self) -> QLabel:
        header = QLabel("Orden de ejecución: ")
        header.setStyleSheet(label_style)
        return header
    

    def _process_queue(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.layout_process_queue = QVBoxLayout()
        container.setLayout(self.layout_process_queue)
        self.layout_process_queue.addStretch()

        scroll.setWidget(container)

        return scroll
    

    def _process_card(self, pcb: Pcb) -> QFrame:
        widget = QFrame()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        widget.setFixedHeight(120)

        layout.setSpacing(0)
        layout.setContentsMargins(16, 0, 16, 0)
        
        layout.addWidget(self._top_card(pcb))
        layout.addWidget(self._mid_card(pcb))
        layout.addWidget(self._bar_card(pcb))
        layout.addWidget(self._btm_card(pcb))

        return widget
    

    def _top_card(self, pcb: Pcb) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)

        pid_frame = self._to_frame(f"[PID {pcb.pid}] {pcb.name}")
        layout.addWidget(pid_frame)

        layout.addStretch()

        state_frame = self._to_frame(f"{pcb.state}")
        layout.addWidget(state_frame)

        return widget
    

    def _mid_card(self, pcb: Pcb) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)
        
        sched = pcb.info_scheduler

        burst_frame = self._to_frame(f"Burst: {sched.burst_time}")
        layout.addWidget(burst_frame)

        memory_frame = self._to_frame(f"Mem: {pcb.info_memory.required_memory}")
        layout.addWidget(memory_frame)
        
        remaining_frame = self._to_frame(f"Rest: {sched.remaining_time}")
        layout.addWidget(remaining_frame)

        pc_frame = self._to_frame(f"PC: 0x{pcb.cpu_context.program_counter}")
        layout.addWidget(pc_frame)

        layout.addStretch()

        return widget


    def _bar_card(self, pcb: Pcb) -> QProgressBar:
        progress_bar = QProgressBar()

        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setFormat("%p%")
        progress_bar.setFixedHeight(5)

        return progress_bar


    def _btm_card(self, pcb: Pcb) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)

        sched = pcb.info_scheduler

        arrival_frame = self._to_frame(f"Lleg: {sched.arrival_time}")
        layout.addWidget(arrival_frame)
        
        turnaround_frame = self._to_frame(f"TAT: {sched.turnaround_time}")
        layout.addWidget(turnaround_frame)

        response_frame = self._to_frame(f"Resp: {sched.response_time}")
        layout.addWidget(response_frame)

        if self.alg == "pr":
            priority_frame = self._to_frame(f"Pr: {sched.priority}")
            layout.addWidget(priority_frame)

        layout.addStretch()

        return widget


    def _to_frame(self, text: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("infoFrame")
        frame.setStyleSheet(frame_style)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 2, 8, 2)

        label = QLabel(text)
        layout.addWidget(label)

        return frame


    def add_process_card(self, pcb: Pcb):
        card = self._process_card(pcb)

        self.layout_process_queue.insertWidget(
            self.layout_process_queue.count() - 1,
            card
        )


    def _footer(self) -> QLabel:
        footer = QLabel("0 proceso(s) en cola.")
        footer.setStyleSheet(label_style)
        return footer
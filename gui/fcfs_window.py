import random

from PySide6.QtWidgets import QProgressBar, QScrollArea, QFrame, QSlider, QSpinBox, QDoubleSpinBox, QPushButton, QLineEdit, QWidget, QGridLayout, QSplitter, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main_window import MainWindow

from models.process import Process

from models.pcb import Pcb
from models.cpu_context    import Cpu_Context
from models.info_scheduler import Info_Scheduler
from models.info_io        import Info_Io
from models.info_error     import Info_Error

class FCFS_Window(QWidget):
    def __init__(self, main_window: "MainWindow"):
        super().__init__()

        self.main_window = main_window

        self.process_queue: list[Process] = []
        self.ready_queue:   list[Process] = []

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        main_layout.addWidget(self.build_header(), 1)
        main_layout.addWidget(self.build_center(), 8)
        main_layout.addWidget(self.build_bottom(), 1)


    def build_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout()

        header.setLayout(layout)

        btn_back = QPushButton("Back")
        btn_back.clicked.connect(self.go_back)

        title = QLabel("FCFS Scheduler")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            
        """)

        sub_title = QLabel("First Come, First Serve")
        sub_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_title.setStyleSheet("""
            
        """)

        total_time = QLabel("u.t. ->")
        total_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_time.setStyleSheet("""
            
        """)

        state = QLabel(" - ")
        state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state.setStyleSheet("""
            
        """)
        
        layout.addWidget(btn_back)
        layout.addWidget(title)
        layout.addWidget(sub_title)
        layout.addWidget(total_time)
        layout.addWidget(state)

        return header


    def build_center(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        widget.setLayout(layout)

        splitter = QSplitter()

        splitter.addWidget(self._build_left_side())
        splitter.addWidget(self._build_right_side())

        layout.addWidget(splitter)

        return widget


    def _build_left_side(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(self._build_enter_process())
        layout.addWidget(self._build_queue_process())

        widget.setLayout(layout)

        return widget


    def _build_enter_process(self) -> QWidget:
        # enter process ##########################################
        wid_ep = QWidget()
        lay_ep = QVBoxLayout()

        # grid_1 = nombre, cpu_burst, memoria, llegada ###########
        wid_grid_1 = QWidget()
        grid_1 = QGridLayout()

        label_name = QLabel("Nombre:")

        label_cpu = QLabel("CPU Burst:")

        label_memory = QLabel("Memoria:")

        label_arrive = QLabel("Llegada:")

        grid_1.addWidget(label_name, 0, 0)
        grid_1.addWidget(label_cpu, 1, 0)
        grid_1.addWidget(label_memory, 2, 0)
        grid_1.addWidget(label_arrive, 3, 0)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("P1, P2, ...")

        self.input_cpu = QDoubleSpinBox()
        self.input_cpu.setMinimum(1)
        self.input_cpu.setMaximum(999999)
        self.input_cpu.setValue(10.0)
        self.input_cpu.setSuffix(" u.t.")

        self.input_memory = QSpinBox()
        self.input_memory.setMinimum(1)
        self.input_memory.setMaximum(999999)
        self.input_memory.setValue(128)
        self.input_memory.setSuffix(" KB")

        self.input_arrival = QDoubleSpinBox()
        self.input_arrival.setMinimum(0.0)
        self.input_arrival.setMaximum(999999.9)
        self.input_arrival.setValue(0.0)
        self.input_arrival.setSuffix(" u.t.")

        grid_1.addWidget(self.input_name, 0, 1)
        grid_1.addWidget(self.input_cpu, 1, 1)
        grid_1.addWidget(self.input_memory, 2, 1)
        grid_1.addWidget(self.input_arrival, 3, 1)
        
        wid_grid_1.setLayout(grid_1)

        lay_ep.addWidget(wid_grid_1)
        ##################################################
        # input area #####################################
        wid_grid_2 = QWidget()
        grid_2 = QGridLayout()

        self.btn_add    = QPushButton("✚ Agregar Proceso")
        self.btn_random = QPushButton("⚄ Aleatorio")
        self.btn_start  = QPushButton("▶ Iniciar FCFS")
        self.btn_stop = QPushButton("⏸")
        self.btn_kill = QPushButton("⏹")

        self.btn_add.clicked.connect(self._add_process)
        self.btn_random.clicked.connect(self._random_process)

        grid_2.addWidget(self.btn_add, 0, 0, 1, 3)
        grid_2.addWidget(self.btn_random, 0, 3, 1, 3)
        grid_2.addWidget(self.btn_start, 1, 0, 1, 4)
        grid_2.addWidget(self.btn_stop, 1, 4)
        grid_2.addWidget(self.btn_kill, 1, 5)
        
        wid_grid_2.setLayout(grid_2)

        lay_ep.addWidget(wid_grid_2)
        ######################################################
        # Velocidad: #########################################
        wid_speed = QWidget()
        lay_speed = QHBoxLayout()

        label_speed = QLabel("Velocidad:")
        label_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setMinimum(1)
        self.slider_speed.setMaximum(20)
        self.slider_speed.setValue(5)

        self.value_speed = QLabel("5x")
        self.slider_speed.valueChanged.connect(self._update_value_speed)
        self.value_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lay_speed.addWidget(label_speed)
        lay_speed.addWidget(self.slider_speed)
        lay_speed.addWidget(self.value_speed)
        
        wid_speed.setLayout(lay_speed)
        lay_ep.addWidget(wid_speed)
        ########################################################
        # Boton Limpiar Todo ###################################
        self.btn_clean = QPushButton("? Limpiar Todo")
        lay_ep.addWidget(self.btn_clean)
        ########################################################
        
        wid_ep.setLayout(lay_ep)
        return wid_ep

    def _update_value_speed(self, value: int):
        self.value_speed.setText(f"{value}x")

    def _add_process(self):
        process = self._create_process()
        self.process_queue.append(process)

        card = self._build_process(process)

        self.lay_container.insertWidget(
            self.lay_container.count() - 1,
            card
        )

    def _random_process(self):
        for _ in range(5):
            self.input_cpu.setValue(random.randint(5, 30))
            self.input_memory.setValue(random.choice([32, 64, 128, 256, 512, 1024]))
            self.input_arrival.setValue(random.randint(0, 10))

            process = self._create_process()
            self.process_queue.append(process)

            card = self._build_process(process)

            self.lay_container.insertWidget(
                self.lay_container.count() - 1,
                card
            )

    def _build_queue_process(self) -> QWidget:
        wid_qp = QFrame()
        lay_qp = QVBoxLayout()

        wid_qp.setStyleSheet("""
            QFrame {
                border: 1px solid gray;
                border-radius: 7px;
                padding: 6px;
            }
        """)

        # Primer Label #########################################
        label_desc = QLabel("Orden de ejecucion (primero en llegar, primero en ser atendido)")

        lay_qp.addWidget(label_desc)
        ########################################################
        # Procesos #############################################
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.lay_container = QVBoxLayout()
        container.setLayout(self.lay_container)

        self.lay_container.addStretch()

        scroll.setWidget(container)
        lay_qp.addWidget(scroll)
        ########################################################
        # Segundo Label ########################################
        label_bottom = QLabel(f"{len(self.process_queue)} proceso(s) en la cola.")
        lay_qp.addWidget(label_bottom)
        ########################################################

        wid_qp.setLayout(lay_qp)
        return wid_qp
    
    def _build_process(self, process: Process) -> QFrame:
        wid_card = QFrame()
        lay_card = QGridLayout()
        wid_card.setStyleSheet("""
            QFrame {
                border: 1px solid gray;
                border-radius: 7px;
                padding: 6px;
            }
            QLabel {
                font-size: 8px;
                border: 1px solid gray;
            }
            QProgressBar {
                font-size: 10px;
            }
        """)

        pcb = process.pcb

        lay_card.addWidget(QLabel(f"[PID {pcb.pid}] {process.name}"), 0, 0)
        lay_card.addWidget(QLabel(f"{pcb.state}"), 0, 4)

        lay_card.addWidget(QLabel(f"Burst: {pcb.cpu_burst}"), 1, 0)
        lay_card.addWidget(QLabel(f"Restante: {pcb.remaining_time}"), 1, 1)
        lay_card.addWidget(QLabel(f"Memoria: {pcb.memory_required}"), 1, 2)
        lay_card.addWidget(QLabel(f"Llegada: {pcb.arrival_time}"), 1, 3)
        lay_card.addWidget(QLabel(f"Prioridad: {pcb.priority}"), 1, 4)

        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setFormat("%p%")
        lay_card.addWidget(progress_bar, 3, 0, 1, 5)

        wid_card.setLayout(lay_card)
        return wid_card

    def _create_process(self) -> Process:
        name = self.input_name.text().strip()

        if name == "":
            name = f"P{len(self.process_queue) + 1}"

        cpu_burst = self.input_cpu.value()

        pcb = Pcb(
            pid = len(self.process_queue) + 1,
            state = "NUEVO",
            pc = 0,
            arrival_time = self.input_arrival.value(),
            cpu_burst = cpu_burst,
            remaining_time = cpu_burst,
            priority = 0,
            memory_required = self.input_memory.value()
        )

        process = Process(
            name = name,
            pcb = pcb,
            cpu_context = Cpu_Context(),
            info_io = Info_Io(),
            info_scheduler = Info_Scheduler(),
            info_error = Info_Error()
        )

        return process
    

    def _build_right_side(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        widget.setLayout(layout)

        return widget
    

    def build_bottom(self) -> QWidget:
        bottom = QWidget()
        layout = QHBoxLayout()

        bottom.setLayout(layout)

        return bottom
    

    def go_back(self):
        self.main_window.show_main_menu()
import random

from PySide6.QtWidgets import QWidget, QVBoxLayout

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main_window import MainWindow

from core.simulator import Simulator

from gui.components.header import Header
from gui.components.center import Center
from gui.components.footer import Footer

from models.process_data import Process_Data

class SJFa_Window(QWidget):
    def __init__(self, main_window: "MainWindow", simulator: Simulator):
        super().__init__()
        self.simulator = simulator

        self.main_window = main_window

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self.header = self._header()
        self.center = self._center()
        self.footer = self._footer()

        main_layout.addWidget(self.header, 1)
        main_layout.addWidget(self.center, 8)
        main_layout.addWidget(self.footer, 1)
    

    def _header(self):
        header = Header()
        
        header.title.setText("SJF")
        header.desc.setText("Shortest Job First Apropiativo")

        header.btn_back.clicked.connect(self.go_back)

        return header
    

    def _center(self):
        center = Center(self.simulator)

        process_input = center.process_input

        process_input.btn_add.clicked.connect(self.add_process)
        process_input.btn_random.clicked.connect(self.add_random_processes)

        return center

    
    def _footer(self):
        footer = Footer()
        footer.algorithm.setText("SJF (apropiativo)")

        return footer
    

    def add_process(self):
        process_data = self.center.process_input.get_process_data()

        pcb = self.simulator.process_manager.create_process(process_data)
        self.center.process_queue.add_process_card(pcb)


    def add_random_processes(self):
        name = ""
        for _ in range(5):
            cpu_burst = random.randint(10, 50)
            memory = random.randint(1, 16) * 2
            arrival_time = random.randint(1, 50)

            process_data = Process_Data(
                name=name,
                cpu_burst=cpu_burst,
                memory=memory,
                arrival_time=arrival_time
            )

            pcb = self.simulator.process_manager.create_process(process_data)
            self.center.process_queue.add_process_card(pcb)


    def go_back(self):
        self.main_window.show_main_menu()
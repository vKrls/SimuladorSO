from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt

from core.simulator import Simulator
from gui.fcfs_window import FCFS_Window
from gui.sjfa_window import SJFa_Window
from gui.sjfn_window import SJFn_Window
from gui.rr_window import RR_Window
from gui.pra_window import PRa_Window
from gui.prn_window import PRn_Window

class MainWindow(QMainWindow):
    def __init__(self, simulator: Simulator):
        super().__init__()
        self.simulator = simulator

        self.setWindowTitle("Hola")

        self.show_main_menu()


    def show_main_menu(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        title = QLabel("Procesitos")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_panel  = QFrame()
        btn_layout = QVBoxLayout()
        btn_panel.setLayout(btn_layout)

        btn_fcfs = QPushButton("FCFS")
        btn_sjfa  = QPushButton("SJF Apropiativo")
        btn_sjfn  = QPushButton("SJF No Apropiativo")
        btn_rr = QPushButton("Round Robin")
        btn_pra = QPushButton("Priority Apropiativo")
        btn_prn = QPushButton("Priority No Apropiativo")

        btn_layout.addWidget(btn_fcfs)
        btn_layout.addWidget(btn_sjfa)
        btn_layout.addWidget(btn_sjfn)
        btn_layout.addWidget(btn_rr)
        btn_layout.addWidget(btn_pra)
        btn_layout.addWidget(btn_prn)

        btn_fcfs.clicked.connect(self.fcfs_window)
        btn_sjfa.clicked.connect(self.sjfa_window)
        btn_sjfn.clicked.connect(self.sjfn_window)
        btn_rr.clicked.connect(self.rr_window)
        btn_pra.clicked.connect(self.pra_window)
        btn_prn.clicked.connect(self.prn_window)

        main_layout.addWidget(title, 1)
        main_layout.addWidget(btn_panel, 4)

        self.setMinimumSize(400, 400)
        self.resize(400, 400)
        self.center_window()


    def fcfs_window(self):
        fcfs_window = FCFS_Window(self, self.simulator)

        self.setCentralWidget(fcfs_window)
        self.resize(1380, 860)
        self.center_window()


    def sjfa_window(self):
        sjfa_window = SJFa_Window(self, self.simulator)

        self.setCentralWidget(sjfa_window)
        self.resize(1380, 860)
        self.center_window()
    
    
    def sjfn_window(self):
        sjfn_window = SJFn_Window(self, self.simulator)

        self.setCentralWidget(sjfn_window)
        self.resize(1380, 860)
        self.center_window()


    def rr_window(self):
        rr_window = RR_Window(self, self.simulator)

        self.setCentralWidget(rr_window)
        self.resize(1380, 860)
        self.center_window()

    
    def pra_window(self):
        pra_window = PRa_Window(self, self.simulator)

        self.setCentralWidget(pra_window)
        self.resize(1380, 860)
        self.center_window()
    
    
    def prn_window(self):
        prn_window = PRn_Window(self, self.simulator)

        self.setCentralWidget(prn_window)
        self.resize(1380, 860)
        self.center_window()


    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        window = self.geometry()

        center = screen.center()
        window.moveCenter(center)

        self.move(window.topLeft())
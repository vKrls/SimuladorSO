import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from gui.fcfs_window import FCFS_Window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Hola")
        self.resize(600, 400)

        self.show_main_menu()


    def show_main_menu(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        ####################### Titulo ######################
        title = QLabel("Procesitos")                        #
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)    #
        title.setStyleSheet("""                             #
            font-size: 24px;                                #
            font-weight: bold;                              #
            margin: 20px;                                   #
        """)                                                #
        #####################################################

        ###################### Botones ######################
        btn_panel  = QFrame()                               #
        btn_layout = QVBoxLayout()                          #
        btn_panel.setLayout(btn_layout)                     #

        btn_fcfs = QPushButton("FCFS")                      #
        btn_sjf  = QPushButton("SJF")                       #
        btn_rr = QPushButton("Round Robin")                 #
        btn_pr = QPushButton("Priority")                    #

        btn_layout.addWidget(btn_fcfs)                      #
        btn_layout.addWidget(btn_sjf)                       #
        btn_layout.addWidget(btn_rr)                        #
        btn_layout.addWidget(btn_pr)                        #

        btn_fcfs.clicked.connect(self.fcfs_window)          #
        btn_sjf.clicked.connect(self.sjf_window)            #
        btn_rr.clicked.connect(self.rr_window)              #
        btn_pr.clicked.connect(self.pr_window)              #
        #####################################################

        main_layout.addWidget(title, 1)
        main_layout.addWidget(btn_panel, 4)

        self.resize(600, 400)
        self.center_window()


    def fcfs_window(self):
        fcfs_win = FCFS_Window(self)

        self.setCentralWidget(fcfs_win)
        self.resize(1380, 860)
        self.center_window()


    def sjf_window(self):
        print("Hola sjf")


    def rr_window(self):
        print("Hola rr")


    def pr_window(self):
        print("Hola pr")


    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        window = self.geometry()

        center = screen.center()
        window.moveCenter(center)

        self.move(window.topLeft())


app = QApplication(sys.argv)
app.setFont(QFont(".AppleSystemUIFont", 10))

window = MainWindow()
window.show()

app.exec()
import sys

from PySide6.QtWidgets import QApplication

from qt_material import apply_stylesheet # type: ignore

from core.simulator import Simulator
from gui.main_window import MainWindow

simulator = Simulator()

app = QApplication(sys.argv)

apply_stylesheet(app, theme="dark_blue.xml")

window = MainWindow(simulator)
window.show()

app.exec()
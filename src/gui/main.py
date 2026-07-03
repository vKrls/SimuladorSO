import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from gui.windows.main_window import MainWindow
from gui.services.simulation_service import SimulationService
from gui.theme import APP_STYLESHEET


def apply_base_palette(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1c2128"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#00d4ff"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#0d1117"))
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLESHEET)


service = SimulationService()
app = QApplication(sys.argv)
apply_base_palette(app)

window = MainWindow(service)
window.show()

app.exec()

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.factories.window_factory import (
    AlgorithmWindowFactory,
    AlgorithmWindowFactoryItem,
)
from gui.services.simulation_service import SimulationService


class MainWindow(QMainWindow):
    def __init__(self, client: SimulationService):
        super().__init__()
        self.client = client
        self.algorithm_window_factory = AlgorithmWindowFactory(client)
        self.setWindowTitle("Simulador de Planificación")
        self.show_main_menu()

    def show_main_menu(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        header = QFrame()
        header.setObjectName("panel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 16, 18, 16)
        title = QLabel("Simulador de Planificación de Procesos")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #00d4ff; font-size: 28px; font-weight: bold;")
        subtitle = QLabel("CPU, memoria, PCB, Gantt, estadísticas y registro de eventos")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #8b949e; font-size: 11px;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setSpacing(14)
        layout.addLayout(grid, 1)

        cards = self.algorithm_window_factory.menu_items()
        for index, item in enumerate(cards):
            grid.addWidget(self._algorithm_card(item), index // 3, index % 3)

        self.setMinimumSize(900, 560)
        self.resize(1040, 660)
        self.center_window()

    def _algorithm_card(self, item: AlgorithmWindowFactoryItem) -> QFrame:
        card = QFrame()
        card.setObjectName("panel")
        card.setStyleSheet("""
            QFrame#panel { background: #161b22; border: 1px solid #30363d; border-radius: 6px; }
            QFrame#panel:hover { border-color: #00d4ff; }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel(item.name)
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        mode_label = QLabel(item.mode)
        mode_label.setStyleSheet("color: #00d4ff; font-size: 9px;")
        top.addWidget(mode_label)
        layout.addLayout(top)

        description = QLabel(item.description)
        description.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(description)
        detail_label = QLabel(item.detail)
        detail_label.setStyleSheet("color: #484f58; font-size: 10px;")
        layout.addWidget(detail_label)
        layout.addStretch()

        button = QPushButton("Abrir")
        button.setObjectName("primaryButton")
        button.clicked.connect(
            lambda _checked=False, key=item.key: self._open_algorithm(key)
        )
        layout.addWidget(button)
        return card

    def _open_algorithm(self, key: str) -> None:
        self.setCentralWidget(
            self.algorithm_window_factory.create_window(key, self)
        )
        self.resize(1380, 860)
        self.center_window()

    def center_window(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        window = self.geometry()
        window.moveCenter(screen.center())
        self.move(window.topLeft())

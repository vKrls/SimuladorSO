from __future__ import annotations

APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Courier New';
}
QFrame#panel, QGroupBox {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
}
QGroupBox {
    margin-top: 16px;
    padding-top: 8px;
    font-size: 10px;
    color: #8b949e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    color: #8b949e;
}
QLabel {
    border: none;
    background: transparent;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    color: #c9d1d9;
    padding: 4px 8px;
    font-size: 11px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #00d4ff;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    selection-background-color: #102b33;
    selection-color: #00d4ff;
}
QPushButton {
    background: #1c2128;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 11px;
}
QPushButton:hover {
    background: #212a33;
    border-color: #00d4ff66;
    color: #ffffff;
}
QPushButton:pressed {
    background: #0d1117;
}
QPushButton:disabled {
    color: #484f58;
    border-color: #21262d;
    background: #161b22;
}
QPushButton#primaryButton {
    background: #102b33;
    color: #00d4ff;
    border: 1px solid #00d4ff66;
    font-weight: bold;
}
QPushButton#primaryButton:hover {
    background: #00d4ff22;
    border-color: #00d4ff;
}
QPushButton#successButton {
    background: #162817;
    color: #7bc67e;
    border: 1px solid #7bc67e66;
    font-weight: bold;
}
QPushButton#successButton:hover {
    background: #7bc67e22;
    border-color: #7bc67e;
}
QPushButton#dangerButton {
    color: #ff4d6d;
    border-color: #ff4d6d55;
}
QPushButton#dangerButton:hover {
    background: #ff4d6d22;
    border-color: #ff4d6d;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: #161b22;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
}
QScrollBar:horizontal {
    background: #161b22;
    height: 8px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
}
QTableWidget {
    background: #0d1117;
    alternate-background-color: #161b22;
    border: 1px solid #21262d;
    gridline-color: #161b22;
    font-size: 10px;
    selection-background-color: #1c2128;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 4px 6px;
}
QHeaderView::section {
    background: #161b22;
    color: #8b949e;
    border: none;
    border-bottom: 1px solid #30363d;
    padding: 5px 6px;
    font-size: 10px;
}
QTextEdit, QPlainTextEdit {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 4px;
    color: #8b949e;
    font-size: 10px;
}
QSlider::groove:horizontal {
    background: #21262d;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #00d4ff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #00d4ff55;
    border-radius: 2px;
}
QTabWidget::pane {
    border: 1px solid #21262d;
    background: #0d1117;
}
QTabBar::tab {
    background: #161b22;
    color: #8b949e;
    padding: 7px 16px;
    border: 1px solid #21262d;
    border-bottom: none;
    font-size: 10px;
}
QTabBar::tab:selected {
    background: #0d1117;
    color: #00d4ff;
    border-color: #00d4ff55;
}
QTabBar::tab:hover {
    color: #c9d1d9;
}
QProgressBar {
    background: #161b22;
    border: none;
    border-radius: 4px;
    color: transparent;
}
QProgressBar::chunk {
    background: #00d4ff;
    border-radius: 4px;
}
QSplitter::handle {
    background: #21262d;
}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from PySide6.QtWidgets import QWidget

from gui.services.simulation_service import SimulationService
from gui.windows.fcfs_window import FCFS_Window
from gui.windows.pra_window import PRa_Window
from gui.windows.prn_window import PRn_Window
from gui.windows.rr_window import RR_Window
from gui.windows.sjfa_window import SJFa_Window
from gui.windows.sjfn_window import SJFn_Window


@dataclass(frozen=True)
class AlgorithmWindowFactoryItem:
    key: str
    name: str
    description: str
    mode: str
    detail: str
    window_class: Type[QWidget]


class AlgorithmWindowFactory:
    def __init__(self, client: SimulationService):
        self.client = client
        self._items = [
            AlgorithmWindowFactoryItem(
                "fcfs",
                "FCFS",
                "First Come First Served",
                "No apropiativo",
                "Orden por llegada",
                FCFS_Window,
            ),
            AlgorithmWindowFactoryItem(
                "sjf_preemptive",
                "SJF-A",
                "Shortest Job First",
                "Apropiativo",
                "Menor tiempo restante",
                SJFa_Window,
            ),
            AlgorithmWindowFactoryItem(
                "sjf_nonpreemptive",
                "SJF-N",
                "Shortest Job First",
                "No apropiativo",
                "Menor burst disponible",
                SJFn_Window,
            ),
            AlgorithmWindowFactoryItem(
                "round_robin",
                "RR",
                "Round Robin",
                "Apropiativo",
                "Quantum configurable",
                RR_Window,
            ),
            AlgorithmWindowFactoryItem(
                "priority_preemptive",
                "PR-A",
                "Prioridades",
                "Apropiativo",
                "Mayor prioridad disponible",
                PRa_Window,
            ),
            AlgorithmWindowFactoryItem(
                "priority_nonpreemptive",
                "PR-N",
                "Prioridades",
                "No apropiativo",
                "Selección por prioridad",
                PRn_Window,
            ),
        ]

    def menu_items(self) -> list[AlgorithmWindowFactoryItem]:
        return list(self._items)

    def create_window(self, key: str, main_window: QWidget) -> QWidget:
        for item in self._items:
            if item.key == key:
                return item.window_class(main_window, self.client)
        raise ValueError(f"Ventana de algoritmo desconocida: {key}")

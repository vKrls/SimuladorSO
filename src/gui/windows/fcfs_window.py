from gui.windows.algorithm_window import AlgorithmWindow


class FCFS_Window(AlgorithmWindow):
    def __init__(self, main_window, client):
        super().__init__(
            main_window,
            client,
            algorithm="fcfs",
            title="FCFS SCHEDULER",
            description="First Come First Served | Gestión de procesos y memoria",
            footer_text="FCFS (no apropiativo)",
        )

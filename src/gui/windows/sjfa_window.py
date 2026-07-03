from gui.windows.algorithm_window import AlgorithmWindow


class SJFa_Window(AlgorithmWindow):
    def __init__(self, main_window, client):
        super().__init__(
            main_window,
            client,
            algorithm="sjf_preemptive",
            title="SJF APROPIATIVO",
            description="Shortest Job First | Menor tiempo restante",
            footer_text="SJF (apropiativo)",
        )

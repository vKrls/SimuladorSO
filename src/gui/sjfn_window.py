from gui.algorithm_window import AlgorithmWindow


class SJFn_Window(AlgorithmWindow):
    def __init__(self, main_window, client):
        super().__init__(
            main_window,
            client,
            algorithm="sjf_nonpreemptive",
            title="SJF NO APROPIATIVO",
            description="Shortest Job First | Menor burst disponible",
            footer_text="SJF (no apropiativo)",
        )

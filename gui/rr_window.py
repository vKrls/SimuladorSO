from gui.algorithm_window import AlgorithmWindow


class RR_Window(AlgorithmWindow):
    def __init__(self, main_window, client):
        super().__init__(
            main_window,
            client,
            algorithm="round_robin",
            title="ROUND ROBIN",
            description="Planificación circular con quantum configurable",
            footer_text="RR (apropiativo)",
            input_mode="rr",
        )

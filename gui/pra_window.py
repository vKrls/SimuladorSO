from gui.algorithm_window import AlgorithmWindow


class PRa_Window(AlgorithmWindow):
    def __init__(self, main_window, client):
        super().__init__(
            main_window,
            client,
            algorithm="priority_preemptive",
            title="PRIORIDADES APROPIATIVO",
            description="Menor valor numérico representa mayor prioridad",
            footer_text="Prioridades (apropiativo)",
            input_mode="pr",
        )

from gui.algorithm_window import AlgorithmWindow


class PRn_Window(AlgorithmWindow):
    def __init__(self, main_window, client):
        super().__init__(
            main_window,
            client,
            algorithm="priority_nonpreemptive",
            title="PRIORIDADES NO APROPIATIVO",
            description="Selección por prioridad sin desalojo",
            footer_text="Prioridades (no apropiativo)",
            input_mode="pr",
        )

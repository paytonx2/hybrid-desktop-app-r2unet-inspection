from PySide6.QtCore import QThread, Signal


class ModelLoadWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, model_manager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager

    def run(self):
        try:
            self.model_manager.load_models(progress_callback=lambda msg: self.progress.emit(msg))
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(str(e))

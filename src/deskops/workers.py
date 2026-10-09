from PySide6.QtCore import QObject, QRunnable, Signal

from deskops.core.metrics import collect_diagnostics
from deskops.core.processes import collect_top_processes


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)



class ProcessWorker(QRunnable):
    """Coleta processos sem bloquear a interface gráfica."""

    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()

    def run(self):
        try:
            processes = collect_top_processes(limit=10)
            self.signals.finished.emit(processes)
        except Exception as error:
            self.signals.error.emit(str(error))



class DiagnosticsWorker(QRunnable):
    """Executa os diagnósticos sem bloquear a interface."""

    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()

    def run(self):
        try:
            report = collect_diagnostics()
            self.signals.finished.emit(report)
        except Exception as error:
            self.signals.error.emit(str(error))


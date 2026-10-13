from deskops.core.metrics import (
    collect_diagnostics,
    collect_metrics,
)
from PySide6.QtCore import QObject, QRunnable, Signal
from deskops.core.processes import collect_top_processes
from deskops.core.processes import terminate_process
import psutil


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)



class ProcessWorker(QRunnable):
    """Coleta processos sem bloquear a interface gráfica."""

    def __init__(self, limit=10):
        super().__init__()
        self.limit = limit
        self.signals = WorkerSignals()

    def run(self):
        try:
            processes = collect_top_processes(limit=self.limit)
            self.signals.finished.emit(processes)
        except Exception as error:
            self.signals.error.emit(str(error))


class ProcessActionWorker(QRunnable):
    """Executa ações de encerramento sem bloquear a interface."""

    def __init__(self, pid, expected_create_time, force=False, name=None):
        super().__init__()
        self.pid = int(pid)
        self.expected_create_time = expected_create_time
        self.force = force
        self.name = name or f"PID {self.pid}"
        self.signals = WorkerSignals()

    def run(self):
        identity = {
            "pid": self.pid,
            "name": self.name,
            "create_time": self.expected_create_time,
            "force": self.force,
        }

        try:
            terminate_process(
                self.pid,
                self.expected_create_time,
                force=self.force,
            )
            result = {"status": "success", **identity}
        except psutil.NoSuchProcess:
            result = {"status": "already_exited", **identity}
        except Exception as error:
            result = {
                "status": "error",
                **identity,
                "error_type": type(error).__name__,
                "error": str(error),
            }

        self.signals.finished.emit(result)


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


class MetricsWorker(QRunnable):
    """Atualiza métricas sem bloquear a interface gráfica."""

    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()

    def run(self):
        try:
            metrics = collect_metrics()
            self.signals.finished.emit(metrics)
        except Exception as error:
            self.signals.error.emit(str(error))


import sys
import json
import time
import platform
from datetime import datetime
from pathlib import Path

import psutil

from collections import deque
import pyqtgraph as pg

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from PySide6.QtGui import QShortcut, QKeySequence

from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QSizePolicy,
)

STYLE = """
QMainWindow, QWidget {
    background-color: #111318;
    color: #e8eaf0;
    font-family: Sans Serif;
    font-size: 13px;
}
QFrame#sidebar {
    background-color: #191c23;
    border-right: 1px solid #2a2e38;
}
QLabel#brand {
    font-size: 21px;
    font-weight: 700;
    color: #91aaff;
}
QLabel#muted {
    color: #969eae;
}
QLabel#metric {
    font-size: 27px;
    font-weight: 600;
}
QFrame#card {
    background-color: #1b1f28;
    border: 1px solid #303541;
    border-radius: 12px;
}
QPushButton {
    background-color: #7595ff;
    color: #101522;
    border: none;
    border-radius: 7px;
    padding: 10px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #91aaff;
}
QTableWidget {
    background-color: #191c23;
    alternate-background-color: #1b1f28;
    color: #e8eaf0;
    border: 1px solid #303541;
    gridline-color: #303541;
    selection-background-color: #35466e;
}
QHeaderView::section {
    background-color: #252a35;
    color: #e8eaf0;
    padding: 7px;
    border: none;
}
"""


def make_card(title, value):
    card = QFrame()
    card.setObjectName("card")

    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)

    heading = QLabel(title)
    heading.setObjectName("muted")

    metric = QLabel(value)
    metric.setObjectName("metric")

    layout.addWidget(heading)
    layout.addWidget(metric)

    return card, metric


def collect_diagnostics():
    """Coleta métricas e gera alertas sem alterar o sistema."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    cpu = psutil.cpu_percent(interval=1.0)

    uptime_hours = int(
        (time.time() - psutil.boot_time()) / 3600
    )

    alerts = []

    if cpu >= 90:
        alerts.append({
            "level": "warning",
            "message": f"Uso elevado de CPU: {cpu:.0f}%",
        })

    if memory.percent >= 90:
        alerts.append({
            "level": "warning",
            "message": (
                f"Memória quase cheia: {memory.percent:.0f}%"
            ),
        })

    if disk.percent >= 90:
        alerts.append({
            "level": "warning",
            "message": (
                f"Pouco espaço livre na raiz: "
                f"{disk.percent:.0f}% usado"
            ),
        })

    if not alerts:
        alerts.append({
            "level": "ok",
            "message": (
                "Nenhum alerta automático encontrado "
                "nas verificações básicas."
            ),
        })

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "system": {
            "os": platform.system(),
            "distribution": platform.platform(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        },
        "metrics": {
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_total_bytes": memory.total,
            "memory_available_bytes": memory.available,
            "root_disk_percent": disk.percent,
            "root_disk_total_bytes": disk.total,
            "root_disk_free_bytes": disk.free,
            "uptime_hours": uptime_hours,
        },
        "alerts": alerts,
    }



def collect_top_processes(limit=10):
    """Retorna os processos com maior uso recente de CPU."""
    processes = []

    for proc in psutil.process_iter(
        ["pid", "name", "username", "memory_percent"]
    ):
        try:
            # Primeira amostra: inicializa o contador de CPU.
            proc.cpu_percent(interval=None)

            processes.append({
                "process": proc,
                "pid": proc.info["pid"],
                "name": proc.info["name"] or "Unknown",
                "username": proc.info["username"] or "Unknown",
                "memory_percent": (
                    proc.info["memory_percent"] or 0.0
                ),
            })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    # Intervalo menor para uma atualização mais rápida.
    time.sleep(0.5)

    results = []

    for item in processes:
        try:
            cpu_percent = item["process"].cpu_percent(
                interval=None
            )

            results.append({
                "pid": item["pid"],
                "name": item["name"],
                "username": item["username"],
                "memory_percent": item["memory_percent"],
                "cpu_percent": cpu_percent,
            })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    results.sort(
        key=lambda process: process["cpu_percent"],
        reverse=True,
    )

    return results[:limit]


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

class DeskOps(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DeskOps")
        screen = QApplication.primaryScreen().availableGeometry()

        self.resize(
            min(1100, screen.width()),
            min(760, screen.height())
        )

        self.setMinimumSize(700, 500)

        #self.fullscreen_shortcut = QShortcut(
         #QKeySequence("F11"),
         #self
        #)
        #self.fullscreen_shortcut.activated.connect(
            #self.toggle_fullscreen
        #)       

        self.last_report = None

        self.cpu_history = deque(maxlen=60)
        self.memory_history = deque(maxlen=60)

        self.thread_pool = QThreadPool.globalInstance()
        self.process_scan_running = False

        self.process_timer = QTimer(self)
        self.process_timer.setInterval(2000)
        self.process_timer.timeout.connect(self.refresh_processes)

        self.diagnostics_running = False

        self.diagnostics_timer = QTimer(self)
        self.diagnostics_timer.setInterval(1000)
        self.diagnostics_timer.timeout.connect(
            self.refresh_diagnostics
        )

        root = QWidget()
        self.setCentralWidget(root)

        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)

        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(20, 24, 20, 20)
        nav.setSpacing(14)

        brand = QLabel("DeskOps")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        nav.addSpacing(20)

        for name in [
            "Overview",
            "Hardware",
            "Diagnostics",
            "Reports",
            "Settings",
        ]:
            item = QLabel(name)
            item.setContentsMargins(8, 10, 8, 10)
            nav.addWidget(item)

        nav.addStretch()

        version = QLabel("Linux Diagnostics · 0.3")
        version.setObjectName("muted")
        nav.addWidget(version)

        # Main content with responsive scrolling
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        page = QVBoxLayout(content)
        page.setContentsMargins(30, 28, 30, 28)
        page.setSpacing(16)

        title = QLabel("System Overview")
        title.setStyleSheet(
            "font-size: 25px; font-weight: 700;"
        )

        subtitle = QLabel(
            f"{platform.system()} · Kernel {platform.release()}"
        )
        subtitle.setObjectName("muted")

        page.addWidget(title)
        page.addWidget(subtitle)

        # Metric cards
        cards = QHBoxLayout()
        cards.setSpacing(14)

        card_cpu, self.cpu_value = make_card("CPU Usage", "--")
        card_mem, self.mem_value = make_card("Memory Used", "--")
        card_disk, self.disk_value = make_card("Disk Used", "--")

        for card in [card_cpu, card_mem, card_disk]:
            cards.addWidget(card)

        page.addLayout(cards)

        # Gráficos históricos
        pg.setConfigOptions(antialias=True)

        self.cpu_plot = pg.PlotWidget(title="CPU Usage — Last 60 Seconds")
        self.cpu_plot.setYRange(0, 100)
        self.cpu_plot.setLabel("left", "Usage", units="%")
        self.cpu_plot.setLabel("bottom", "Sample", units="s")
        self.cpu_plot.showGrid(x=True, y=True, alpha=0.3)
        self.cpu_curve = self.cpu_plot.plot(
            pen=pg.mkPen("#91aaff", width=2)
        )

        self.memory_plot = pg.PlotWidget(
            title="Memory Usage — Last 60 Seconds"
        )
        self.memory_plot.setYRange(0, 100)
        self.memory_plot.setLabel("left", "Usage", units="%")
        self.memory_plot.setLabel("bottom", "Sample", units="s")
        self.memory_plot.showGrid(x=True, y=True, alpha=0.3)
        self.memory_curve = self.memory_plot.plot(
            pen=pg.mkPen("#70d6a5", width=2)
        )

        self.cpu_curve.setData([10, 25, 15, 40, 30, 60, 45])
        self.memory_curve.setData([50, 52, 48, 55, 53, 65, 60])

        self.cpu_plot.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.memory_plot.setSizePolicy(
          QSizePolicy.Policy.Expanding,
          QSizePolicy.Policy.Expanding
        )

        page.addWidget(self.cpu_plot)
        page.addWidget(self.memory_plot)

        self.status = QLabel("Ready to inspect this system.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        page.addWidget(self.status)

        # Diagnostic and export buttons
        scan = QPushButton("Run System Diagnostics")
        scan.clicked.connect(self.run_diagnostics)
        page.addWidget(scan)

        export = QPushButton("Export JSON Report")
        export.clicked.connect(self.export_report)
        page.addWidget(export)

        # Process table
        process_title = QLabel("Top Processes")
        process_title.setStyleSheet(
            "font-size: 18px; font-weight: 700;"
        )
        page.addWidget(process_title)

        self.process_table = QTableWidget(0, 5)
        self.process_table.setHorizontalHeaderLabels([
            "PID",
            "Process",
            "CPU %",
            "Memory %",
            "User",
        ])

        self.process_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.process_table.setAlternatingRowColors(True)
        self.process_table.setMinimumHeight(220)
        self.process_table.setSortingEnabled(False)

        page.addWidget(self.process_table)

        refresh = QPushButton("Refresh Process List")
        refresh.clicked.connect(self.refresh_processes)
        page.addWidget(refresh)

        page.addStretch()

        scroll.setWidget(content)

        main.addWidget(sidebar)
        main.addWidget(scroll, 1)

        # Initial data
        self.run_diagnostics()
        self.refresh_processes()

        self.diagnostics_timer.start()
        self.process_timer.start()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def run_diagnostics(self):
        self.refresh_diagnostics()


    def on_diagnostics_error(self, message):
        self.diagnostics_running = False
        self.status.setText(
            f"Could not complete diagnostics: {message}"
        )

    def export_report(self):
        if self.last_report is None:
            QMessageBox.warning(
                self,
                "No report",
                "Run diagnostics first.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save diagnostic report",
            str(Path.home() / "deskops-report.json"),
            "JSON files (*.json)",
        )

        if not filename:
            return

        try:
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(
                    self.last_report,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            QMessageBox.information(
                self,
                "Report saved",
                f"Diagnostic report saved to:\n{filename}",
            )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Export failed",
                f"Could not save report:\n{error}",
            )

    
    def refresh_processes(self):
        # Impede que uma nova coleta comece antes da anterior terminar.
        if self.process_scan_running:
            return

        self.process_scan_running = True
        self.status.setText("Collecting process information...")

        worker = ProcessWorker()
        worker.signals.finished.connect(self.on_processes_ready)
        worker.signals.error.connect(self.on_processes_error)

        self.thread_pool.start(worker)


    def on_processes_ready(self, processes):
        self.process_scan_running = False

        self.process_table.setRowCount(len(processes))

        for row, proc in enumerate(processes):
            values = [
                str(proc["pid"]),
                proc["name"],
                f'{proc["cpu_percent"]:.1f}',
                f'{proc["memory_percent"]:.2f}',
                proc["username"],
            ]

            for column, value in enumerate(values):
                self.process_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        self.status.setText(
            f"Process scan complete: {len(processes)} "
            "processes displayed."
        )


    def on_processes_error(self, message):
        self.process_scan_running = False
        self.status.setText(
            f"Could not inspect processes: {message}"
        )


    def refresh_diagnostics(self):
        if self.diagnostics_running:
            return

        self.diagnostics_running = True

        worker = DiagnosticsWorker()
        worker.signals.finished.connect(
            self.on_diagnostics_ready
        )
        worker.signals.error.connect(
            self.on_diagnostics_error
        )

        self.thread_pool.start(worker)


    def on_diagnostics_ready(self, report):
        self.diagnostics_running = False
        self.last_report = report

        metrics = report["metrics"]

        self.cpu_value.setText(
            f'{metrics["cpu_percent"]:.0f}%'
        )
        self.mem_value.setText(
            f'{metrics["memory_percent"]:.0f}%'
        )
        self.disk_value.setText(
            f'{metrics["root_disk_percent"]:.0f}%'
        )

        warnings = sum(
            alert["level"] == "warning"
            for alert in report["alerts"]
        )

        if warnings:
            summary = f"{warnings} warning(s) found."
        else:
            summary = "System metrics updated successfully."

        self.status.setText(
            f"{summary} "
            f'Uptime: {metrics["uptime_hours"]} hours.'
        )

        self.cpu_history.append(metrics["cpu_percent"])
        self.memory_history.append(metrics["memory_percent"])

        self.cpu_curve.setData(list(self.cpu_history))
        self.memory_curve.setData(list(self.memory_history))

        self.cpu_plot.setMinimumHeight(200)
        self.memory_plot.setMinimumHeight(200)

        self.cpu_history.append(float(metrics["cpu_percent"]))
        self.memory_history.append(float(metrics["memory_percent"]))

        self.cpu_curve.setData(
            list(range(len(self.cpu_history))),
            list(self.cpu_history),
        )

        self.memory_curve.setData(
         list(range(len(self.memory_history))),
          list(self.memory_history),
        )   



def on_diagnostics_error(self, message):
    self.diagnostics_running = False
    self.status.setText(
        f"Could not complete diagnostics: {message}"
    )

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    window = DeskOps()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()


import sys
import json
import platform
from pathlib import Path


from deskops.workers import ProcessWorker, DiagnosticsWorker

from collections import deque
import pyqtgraph as pg

from PySide6.QtCore import QThreadPool, QTimer

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

import platform

import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QHeaderView,
    QScrollArea,
    QSizePolicy,
)


BG = "#0c1018"
PANEL = "#141b27"
BORDER = "#273247"
TEXT = "#edf2fc"
MUTED = "#8592a8"
BLUE = "#8ba5ff"
GREEN = "#6de0b1"
AMBER = "#f2c477"


def label(text, name=None):
    item = QLabel(text)
    if name:
        item.setObjectName(name)
    return item


def make_card(title, value, accent, symbol, description):
    card = QFrame()
    card.setObjectName("metricCard")
    card.setMinimumHeight(136)

    root = QVBoxLayout(card)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    stripe = QFrame()
    stripe.setFixedHeight(3)
    stripe.setStyleSheet(
        f"background-color: {accent}; border: none; border-radius: 1px;"
    )
    root.addWidget(stripe)

    body = QWidget()
    body.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(body)
    layout.setContentsMargins(17, 13, 17, 14)
    layout.setSpacing(7)

    top = QHBoxLayout()
    heading = label(title.upper())
    heading.setStyleSheet(
        f"color: {MUTED}; font-size: 10px; font-weight: 700;"
        " letter-spacing: 1px; background: transparent;"
    )

    icon = label(symbol)
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setFixedSize(31, 31)
    icon.setStyleSheet(
        f"color: {accent}; background: #202a3b;"
        " border-radius: 9px; font-size: 16px; font-weight: 700;"
    )

    top.addWidget(heading)
    top.addStretch()
    top.addWidget(icon)
    layout.addLayout(top)

    metric = label(value)
    metric.setStyleSheet(
        f"color: {TEXT}; font-size: 29px; font-weight: 750;"
        " background: transparent;"
    )
    layout.addWidget(metric)

    detail = label(description)
    detail.setStyleSheet(
        f"color: {MUTED}; font-size: 10px; background: transparent;"
    )
    layout.addWidget(detail)

    root.addWidget(body)
    return card, metric


def make_panel(title, subtitle=None):
    panel = QFrame()
    panel.setObjectName("dashboardPanel")

    layout = QVBoxLayout(panel)
    layout.setContentsMargins(17, 15, 17, 16)
    layout.setSpacing(12)

    header = QHBoxLayout()
    header.setSpacing(12)

    titles = QVBoxLayout()
    titles.setSpacing(4)

    heading = label(title)
    heading.setStyleSheet(
        f"color: {TEXT}; font-size: 13px; font-weight: 700;"
        " background: transparent;"
    )
    titles.addWidget(heading)

    if subtitle:
        sub = label(subtitle)
        sub.setStyleSheet(
            f"color: {MUTED}; font-size: 10px; background: transparent;"
        )
        titles.addWidget(sub)

    header.addLayout(titles)
    header.addStretch()
    layout.addLayout(header)

    return panel, layout


class OverviewPage(QWidget):
    """DeskOps system overview dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("overviewRoot")
        self.setStyleSheet(f"""
            QWidget#overviewRoot {{
                background: {BG};
                color: {TEXT};
            }}
            QFrame#metricCard, QFrame#dashboardPanel {{
                background: {PANEL};
                border: 1px solid {BORDER};
                border-radius: 13px;
            }}
            QFrame#dashboardPanel {{
                border-radius: 12px;
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 11px;
                font-weight: 650;
            }}
            QPushButton#primaryButton {{
                background: #526ff5;
                color: #ffffff;
                border: 1px solid #7189ff;
            }}
            QPushButton#primaryButton:hover {{
                background: #6882ff;
                color: #ffffff;
            }}
            QPushButton#primaryButton:pressed {{
                background: #4059d6;
                color: #ffffff;
            }}
            QPushButton#secondaryButton {{
                background: #1a2434;
                color: #dce5f6;
                border: 1px solid #34435c;
            }}
            QPushButton#secondaryButton:hover {{
                background: #253249;
                border-color: #536887;
            }}
            QTableWidget#processTable {{
                background: #111824;
                alternate-background-color: #151e2c;
                color: #dce5f5;
                border: 1px solid #28354a;
                border-radius: 8px;
                gridline-color: transparent;
                selection-background-color: #2b3c60;
                selection-color: #ffffff;
                outline: none;
            }}
            QTableWidget#processTable::item {{
                padding: 6px;
                border: none;
            }}
            QHeaderView::section {{
                background: #1a2434;
                color: #91a1bb;
                padding: 10px 7px;
                border: none;
                border-bottom: 1px solid #344158;
                font-size: 10px;
                font-weight: 700;
            }}
            QScrollArea#pageScroll {{
                border: none;
                background: {BG};
            }}
            QScrollBar:vertical {{
                background: {BG};
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #34435c;
                min-height: 28px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("pageScroll")
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("dashboardContent")
        content.setStyleSheet(f"background: {BG};")

        page = QVBoxLayout(content)
        page.setContentsMargins(25, 23, 25, 26)
        page.setSpacing(18)
        scroll.setWidget(content)

        # Page heading
        heading_row = QHBoxLayout()
        heading_row.setSpacing(15)

        heading_group = QVBoxLayout()
        heading_group.setSpacing(5)

        eyebrow = label("DESKOPS  /  SYSTEM MONITOR")
        eyebrow.setStyleSheet(
            f"color: {BLUE}; font-size: 9px; font-weight: 800;"
            " letter-spacing: 2px; background: transparent;"
        )

        title = label("System Overview", "pageTitle")
        title.setStyleSheet(
            f"color: {TEXT}; font-size: 27px; font-weight: 750;"
            " background: transparent;"
        )

        subtitle = label(
            f"{platform.system()}  ·  Kernel {platform.release()}"
        )
        subtitle.setStyleSheet(
            f"color: {MUTED}; font-size: 11px; background: transparent;"
        )

        heading_group.addWidget(eyebrow)
        heading_group.addWidget(title)
        heading_group.addWidget(subtitle)

        heading_row.addLayout(heading_group)
        heading_row.addStretch()

        self.status = label("●  MONITORING")
        self.status.setObjectName("statusBadge")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setMinimumWidth(125)
        self.status.setStyleSheet(
            f"color: {GREEN}; background: #142b28;"
            " border: 1px solid #285047; border-radius: 9px;"
            " padding: 10px 12px; font-size: 10px; font-weight: 750;"
        )
        heading_row.addWidget(
            self.status, 0, Qt.AlignmentFlag.AlignVCenter
        )

        page.addLayout(heading_row)

        # Section heading
        section = QHBoxLayout()
        section_title = label("Resource utilization")
        section_title.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; font-weight: 700;"
            " background: transparent;"
        )
        section_note = label("LIVE SYSTEM METRICS")
        section_note.setStyleSheet(
            f"color: {MUTED}; font-size: 9px; font-weight: 700;"
            " letter-spacing: 1px; background: transparent;"
        )
        section.addWidget(section_title)
        section.addStretch()
        section.addWidget(section_note)
        page.addLayout(section)

        cards = QHBoxLayout()
        cards.setSpacing(13)

        card_cpu, self.cpu_value = make_card(
            "Processor", "--", BLUE, "⌁", "Total CPU utilization"
        )
        card_mem, self.mem_value = make_card(
            "Memory", "--", GREEN, "▤", "Physical RAM utilization"
        )
        card_disk, self.disk_value = make_card(
            "Storage", "--", AMBER, "▣", "Root filesystem utilization"
        )
        card_temp, self.temp_value = make_card(
            "Temperature", "Unavailable", "#fb7185", "°",
            "Highest CPU core temperature"
        )

        for card in (card_cpu, card_mem, card_disk, card_temp):
            cards.addWidget(card, 1)

        page.addLayout(cards)

        # Performance charts
        chart_heading = QHBoxLayout()
        chart_label = label("Performance history")
        chart_label.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; font-weight: 700;"
            " background: transparent;"
        )
        chart_hint = label("RECENT SAMPLES")
        chart_hint.setStyleSheet(
            f"color: {MUTED}; font-size: 9px; font-weight: 700;"
            " letter-spacing: 1px; background: transparent;"
        )
        self.reset_zoom_button = QPushButton("Reset Zoom")
        self.reset_zoom_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_zoom_button.setToolTip("Restore full history and 0–100% scale")
        self.reset_zoom_button.setStyleSheet(
            "QPushButton { background: #202b3b; color: #cbd6e8; "
            "border: 1px solid #344158; border-radius: 6px; "
            "padding: 5px 9px; font-size: 10px; font-weight: 600; } "
            "QPushButton:hover { background: #2b394d; }"
        )
        self.reset_zoom_button.clicked.connect(self.reset_zoom)
        chart_heading.addWidget(chart_label)
        chart_heading.addStretch()
        chart_heading.addWidget(self.reset_zoom_button)
        chart_heading.addWidget(chart_hint)
        page.addLayout(chart_heading)

        pg.setConfigOptions(antialias=True)

        self.cpu_plot = pg.PlotWidget()
        self.memory_plot = pg.PlotWidget()

        self._configure_plot(self.cpu_plot, "CPU", BLUE)
        self._configure_plot(self.memory_plot, "MEMORY", GREEN)

        self.cpu_curve = self.cpu_plot.plot(
            pen=pg.mkPen(BLUE, width=2.5)
        )
        self.memory_curve = self.memory_plot.plot(
            pen=pg.mkPen(GREEN, width=2.5)
        )

        charts = QHBoxLayout()
        charts.setSpacing(13)

        cpu_panel, cpu_layout = make_panel(
            "Processor activity", "Total utilization over time"
        )
        cpu_layout.addWidget(self.cpu_plot)

        mem_panel, mem_layout = make_panel(
            "Memory activity", "Physical RAM utilization over time"
        )
        mem_layout.addWidget(self.memory_plot)

        charts.addWidget(cpu_panel, 1)
        charts.addWidget(mem_panel, 1)
        page.addLayout(charts)

        # Diagnostics report
        report_panel, report_layout = make_panel(
            "Diagnostics", "System health and latest scan results"
        )

        self.diagnostics_result = QLabel(
            "No diagnostic report yet. Run a scan to inspect system health."
        )
        self.diagnostics_result.setWordWrap(True)
        self.diagnostics_result.setMinimumHeight(45)
        self.diagnostics_result.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.diagnostics_result.setStyleSheet(
            "color: #cbd6e8; background: #101722;"
            " border: 1px solid #263349; border-radius: 8px;"
            " padding: 12px; font-size: 11px;"
        )
        report_layout.addWidget(self.diagnostics_result)
        page.addWidget(report_panel)

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(10)

        self.scan_button = QPushButton("Run diagnostics")
        self.scan_button.setObjectName("primaryButton")

        self.export_button = QPushButton("Export JSON")
        self.export_button.setObjectName("secondaryButton")

        self.refresh_button = QPushButton("Refresh processes")
        self.refresh_button.setObjectName("secondaryButton")

        actions.addWidget(self.scan_button)
        actions.addWidget(self.export_button)
        actions.addStretch()
        actions.addWidget(self.refresh_button)
        page.addLayout(actions)

        # Process table
        process_panel, process_layout = make_panel(
            "Top processes", "Processes currently consuming system resources"
        )

        self.process_table = QTableWidget(0, 5)
        self.process_table.setObjectName("processTable")
        self.process_table.setHorizontalHeaderLabels([
            "PID", "PROCESS", "CPU %", "MEMORY %", "USER"
        ])

        self.process_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.process_table.verticalHeader().setVisible(False)
        self.process_table.verticalHeader().setDefaultSectionSize(35)
        self.process_table.setAlternatingRowColors(True)
        self.process_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.process_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.process_table.setShowGrid(False)
        self.process_table.setMinimumHeight(300)
        self.process_table.setSortingEnabled(False)

        process_layout.addWidget(self.process_table)
        page.addWidget(process_panel)

        footer = label("DESKOPS  •  SYSTEM INTELLIGENCE")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            f"color: #526078; font-size: 9px; font-weight: 700;"
            " letter-spacing: 2px; padding: 9px; background: transparent;"
        )
        page.addWidget(footer)

        page.addStretch()

    def reset_zoom(self):
        """Restore both charts to the full available history."""
        for plot, curve in (
            (self.cpu_plot, self.cpu_curve),
            (self.memory_plot, self.memory_curve),
        ):
            x_data, _ = curve.getData()
            if x_data is None or len(x_data) == 0:
                plot.setXRange(0, 59, padding=0)
            else:
                left = float(x_data[0])
                right = float(x_data[-1])
                if right <= left:
                    right = left + 1.0
                plot.setXRange(left, right, padding=0.02)
            plot.setYRange(0, 100, padding=0)

    @staticmethod
    def _configure_plot(plot, title, accent):
        plot.setBackground(PANEL)
        plot.setMinimumHeight(190)
        plot.setMaximumHeight(250)
        plot.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        plot.setTitle(
            title, color="#a9b8d0", size="10pt"
        )
        plot.setYRange(0, 100)
        plot.setLabel("left", "Usage", units="%")
        plot.setLabel("bottom", "Sample")
        plot.showGrid(x=True, y=True, alpha=0.13)
        plot.setMenuEnabled(False)
        plot.getPlotItem().hideButtons()
        plot.setMouseEnabled(x=True, y=True)

        for axis_name in ("left", "bottom"):
            axis = plot.getAxis(axis_name)
            axis.setPen("#344158")
            axis.setTextPen("#8493ad")
            axis.setStyle(tickTextOffset=8)

    @staticmethod
    def _panel(widget):
        panel = QFrame()
        panel.setObjectName("dashboardPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(widget)

        return panel

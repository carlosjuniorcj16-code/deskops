
import sys
import signal
import json
import platform
from pathlib import Path


from deskops.workers import (
    ProcessWorker,
    DiagnosticsWorker,
    MetricsWorker,
)
from deskops.ui.pages.overview import OverviewPage

from collections import deque
import pyqtgraph as pg

from PySide6.QtCore import QThreadPool, QTimer, Qt

from PySide6.QtGui import QShortcut, QKeySequence, QColor, QPalette

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
    QStackedWidget,
    QSizePolicy,
    QSpinBox,
    QColorDialog,
    QComboBox,
)

STYLE = """
QMainWindow, QWidget {
    background-color: #0c1018;
    color: #e5eaf3;
    font-family: "Sans Serif";
    font-size: 12px;
}

QWidget#pageContent {
    background-color: #0c1018;
}

QScrollArea#pageScroll {
    border: none;
    background-color: #0c1018;
}

QFrame#sidebar {
    background-color: #151a24;
    border-right: 1px solid #292f3d;
}

QLabel#brand {
    font-size: 22px;
    font-weight: 700;
    color: #a5b4fc;
}

QLabel#muted {
    color: #8e9aaf;
    font-size: 11px;
}

QLabel#pageTitle {
    color: #f1f5fb;
    font-size: 25px;
    font-weight: 700;
}

QLabel#metricHeading {
    color: #929db1;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#metric {
    font-size: 27px;
    font-weight: 700;
}

QFrame#metricCard,
QFrame#chartPanel,
QFrame#reportPanel {
    background-color: #141b27;
    border: 1px solid #273247;
    border-radius: 10px;
}

QLabel#sectionHeading {
    color: #aab6ca;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#statusBadge {
    background-color: #1c302c;
    color: #8be0b2;
    border: 1px solid #2b4a40;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 10px;
    font-weight: 600;
}

QLabel#reportText {
    color: #d1d9e7;
    background-color: #151b26;
    border: 1px solid #293345;
    border-radius: 7px;
    padding: 10px;
    font-size: 11px;
}

QPushButton {
    border-radius: 7px;
    padding: 9px 13px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton#primaryButton {
    background-color: #526ff5;
    color: #ffffff;
    border: 1px solid #7189ff;
}

QPushButton#primaryButton:hover {
    background-color: #6882ff;
}

QPushButton#primaryButton:pressed {
    background-color: #4059d6;
}

QPushButton#secondaryButton {
    background-color: #202735;
    color: #dce4f2;
    border: 1px solid #354055;
}

QPushButton#secondaryButton:hover {
    background-color: #293346;
    border-color: #53627e;
}

QTableWidget#processTable {
    background-color: #171d28;
    alternate-background-color: #1b2230;
    color: #dce4f2;
    border: 1px solid #2b3444;
    border-radius: 7px;
    gridline-color: transparent;
    selection-background-color: #303e61;
    selection-color: #ffffff;
    outline: none;
}

QTableWidget#processTable::item {
    padding: 5px;
    border: none;
}

QHeaderView::section {
    background-color: #202735;
    color: #9eabc0;
    padding: 9px 7px;
    border: none;
    border-bottom: 1px solid #354055;
    font-size: 10px;
    font-weight: 700;
}

QScrollBar:vertical {
    background-color: #11151d;
    width: 9px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #394357;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #52617b;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
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

        self.settings_path = (
            Path.home() / ".config" / "DeskOps" / "settings.json"
        )
        self.preferences = self.load_preferences()
        self.refresh_interval = self.preferences["refresh_interval"]
        self.accent_color = self.preferences["accent_color"]
        self.theme_mode = self.preferences["theme"]

        self.setWindowTitle("DeskOps")
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1240, screen.width()), min(850, screen.height()))
        self.setMinimumSize(760, 560)

        self.last_report = None
        self.cpu_history = deque(maxlen=60)
        self.memory_history = deque(maxlen=60)
        self.thread_pool = QThreadPool.globalInstance()
        self.process_scan_running = False
        self.diagnostics_running = False
        self.metrics_running = False

        self.process_timer = QTimer(self)
        self.process_timer.setInterval(self.refresh_interval)
        self.process_timer.timeout.connect(self.refresh_processes)

        self.metrics_timer = QTimer(self)
        self.metrics_timer.setInterval(self.refresh_interval)
        self.metrics_timer.timeout.connect(self.refresh_metrics)

        root = QWidget()
        root.setStyleSheet("background-color: #0c1018;")
        self.setCentralWidget(root)

        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Navigation rail
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(218)
        sidebar.setStyleSheet("""
            QFrame#sidebar {
                background: #101620;
                border-right: 1px solid #253044;
            }
            QLabel { background: transparent; }
            QPushButton#navButton {
                text-align: left;
                padding: 12px 13px;
                border: 1px solid transparent;
                border-radius: 9px;
                background: transparent;
                color: #94a1b7;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#navButton:hover {
                background: #192334;
                color: #e8efff;
            }
            QPushButton#navButton:checked {
                background: #202d47;
                color: #a9bdff;
                border: 1px solid #34476d;
            }
        """)

        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(15, 22, 15, 17)
        nav.setSpacing(7)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        brand_mark = QLabel("D")
        self.brand_mark = brand_mark
        brand_mark.setFixedSize(37, 37)
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setStyleSheet("""
            color: #101624;
            background: #9bb0ff;
            border-radius: 11px;
            font-size: 22px;
            font-weight: 900;
        """)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)

        brand = QLabel("DeskOps")
        brand.setStyleSheet(
            "color: #f0f4ff; font-size: 18px; font-weight: 800;"
        )
        brand_subtitle = QLabel("LINUX SYSTEM TOOLS")
        brand_subtitle.setStyleSheet(
            "color: #72819a; font-size: 8px; font-weight: 700;"
            " letter-spacing: 1px;"
        )

        brand_text.addWidget(brand)
        brand_text.addWidget(brand_subtitle)
        brand_row.addWidget(brand_mark)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        nav.addLayout(brand_row)
        nav.addSpacing(31)

        nav_label = QLabel("WORKSPACE")
        nav_label.setStyleSheet(
            "color: #66758e; font-size: 9px; font-weight: 800;"
            " letter-spacing: 1.5px; padding: 0 10px 7px;"
        )
        nav.addWidget(nav_label)

        self.pages = QStackedWidget()
        self.pages.setStyleSheet(
            "QStackedWidget { background: #0c1018; border: none; }"
        )

        self.overview = OverviewPage()
        self.pages.addWidget(self.overview)

        def build_page(title, subtitle, entries, action_text=None,
                       action_callback=None):
            page = QWidget()
            page.setStyleSheet("""
                QWidget { background: #0c1018; color: #e7edf8; }
                QFrame#infoCard {
                    background: #141b27;
                    border: 1px solid #29364a;
                    border-radius: 12px;
                }
            """)

            layout = QVBoxLayout(page)
            layout.setContentsMargins(32, 30, 32, 30)
            layout.setSpacing(17)

            eyebrow = QLabel("DESKOPS  /  SYSTEM TOOLS")
            eyebrow.setStyleSheet(
                "color: #91aaff; font-size: 9px; font-weight: 800;"
                " letter-spacing: 2px;"
            )

            heading = QLabel(title)
            heading.setStyleSheet(
                "color: #f0f4ff; font-size: 28px; font-weight: 800;"
            )

            description = QLabel(subtitle)
            description.setWordWrap(True)
            description.setStyleSheet(
                "color: #8d9bb1; font-size: 12px;"
            )

            layout.addWidget(eyebrow)
            layout.addWidget(heading)
            layout.addWidget(description)
            layout.addSpacing(7)

            value_labels = []

            for entry_title, entry_value in entries:
                card = QFrame()
                card.setObjectName("infoCard")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(19, 16, 19, 17)
                card_layout.setSpacing(8)

                key = QLabel(entry_title.upper())
                key.setStyleSheet(
                    "color: #91a2bd; font-size: 9px;"
                    " font-weight: 800; letter-spacing: 1px;"
                )

                value = QLabel(entry_value)
                value.setWordWrap(True)
                value.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
                value.setStyleSheet(
                    "color: #dce5f5; font-size: 12px;"
                )

                card_layout.addWidget(key)
                card_layout.addWidget(value)
                layout.addWidget(card)
                value_labels.append(value)

            if action_text and action_callback:
                button = QPushButton(action_text)
                button.setObjectName("primaryButton")
                button.setMaximumWidth(230)
                button.clicked.connect(action_callback)
                layout.addWidget(button)

            layout.addStretch()
            return page, value_labels

        hardware_page, _ = build_page(
            "Hardware",
            "A quick view of the environment running DeskOps.",
            [
                ("Operating system",
                 f"{platform.system()} {platform.release()}"),
                ("Architecture", platform.machine()),
                ("Processor", platform.processor() or
                 "Processor identification unavailable"),
                ("Python runtime", platform.python_version()),
                ("Resource monitoring",
                 "CPU, memory and root filesystem utilization are "
                 "collected by the background monitoring worker."),
            ],
        )
        self.pages.addWidget(hardware_page)

        diagnostics_page, diagnostics_labels = build_page(
            "Diagnostics",
            "Run an on-demand scan and review the latest system findings.",
            [
                ("Scan status", "No diagnostic scan has been run yet."),
            ],
            "Run diagnostics",
            self.run_diagnostics,
        )
        self.secondary_report_label = diagnostics_labels[0]
        self.secondary_report_label.setMinimumHeight(190)
        self.secondary_report_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.secondary_report_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.pages.addWidget(diagnostics_page)

        reports_page, reports_labels = build_page(
            "Reports",
            "Diagnostic reports can be exported as JSON for later review.",
            [
                ("Latest report", "Run diagnostics to generate a report."),
                ("Export format", "JSON · UTF-8 · Structured report data"),
            ],
            "Export latest report",
            self.export_report,
        )
        self.reports_status_label = reports_labels[0]
        self.pages.addWidget(reports_page)

        settings_page = QWidget()
        settings_page.setStyleSheet(
            "QWidget { background: #0c1018; color: #e7edf8; }"
        )
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(32, 30, 32, 30)
        settings_layout.setSpacing(16)

        settings_heading = QLabel("Settings")
        settings_heading.setStyleSheet(
            "color: #f0f4ff; font-size: 28px; font-weight: 800;"
        )
        settings_description = QLabel(
            "Customize DeskOps monitoring and appearance."
        )
        settings_description.setWordWrap(True)
        settings_description.setStyleSheet("color: #8d9bb1;")

        settings_layout.addWidget(settings_heading)
        settings_layout.addWidget(settings_description)

        theme_card = QFrame()
        theme_card.setObjectName("infoCard")
        theme_card.setStyleSheet(
            "QFrame#infoCard { background: #141b27;"
            " border: 1px solid #29364a; border-radius: 12px; }"
        )
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(19, 16, 19, 17)
        theme_layout.setSpacing(10)

        theme_label = QLabel("APPLICATION THEME")
        theme_label.setStyleSheet(
            "color: #91a2bd; font-size: 10px; font-weight: 800;"
        )
        theme_help = QLabel(
            "Choose dark, light, or follow your system appearance."
        )
        theme_help.setWordWrap(True)
        theme_help.setStyleSheet("color: #8d9bb1;")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.theme_combo.setCurrentText(self.theme_mode.title())
        self.theme_combo.setMaximumWidth(220)
        self.theme_combo.currentTextChanged.connect(self.change_theme)

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_help)
        theme_layout.addWidget(self.theme_combo)
        settings_layout.addWidget(theme_card)

        interval_card = QFrame()
        interval_card.setObjectName("infoCard")
        interval_card.setStyleSheet(
            "QFrame#infoCard { background: #141b27;"
            " border: 1px solid #29364a; border-radius: 12px; }"
        )
        interval_layout = QVBoxLayout(interval_card)
        interval_layout.setContentsMargins(19, 16, 19, 17)
        interval_layout.setSpacing(10)

        interval_label = QLabel("MONITORING REFRESH INTERVAL")
        interval_label.setStyleSheet(
            "color: #91a2bd; font-size: 10px; font-weight: 800;"
        )
        interval_help = QLabel(
            "Choose how often CPU, memory and process data refresh."
        )
        interval_help.setWordWrap(True)
        interval_help.setStyleSheet("color: #8d9bb1;")

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 10)
        self.interval_spin.setSuffix(" seconds")
        self.interval_spin.setValue(
            max(1, min(10, round(self.refresh_interval / 1000)))
        )
        self.interval_spin.setMaximumWidth(180)
        self.interval_spin.setStyleSheet(
            "QSpinBox { background: #0c1018; color: #e7edf8;"
            " border: 1px solid #34435b; border-radius: 6px;"
            " padding: 7px; }"
        )
        self.interval_spin.valueChanged.connect(
            self.change_refresh_interval
        )

        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(interval_help)
        interval_layout.addWidget(self.interval_spin)
        settings_layout.addWidget(interval_card)

        accent_card = QFrame()
        accent_card.setObjectName("infoCard")
        accent_card.setStyleSheet(
            "QFrame#infoCard { background: #141b27;"
            " border: 1px solid #29364a; border-radius: 12px; }"
        )
        accent_layout = QVBoxLayout(accent_card)
        accent_layout.setContentsMargins(19, 16, 19, 17)
        accent_layout.setSpacing(10)

        accent_label = QLabel("ACCENT COLOR")
        accent_label.setStyleSheet(
            "color: #91a2bd; font-size: 10px; font-weight: 800;"
        )
        accent_help = QLabel(
            "Choose the highlight color used by navigation and branding."
        )
        accent_help.setWordWrap(True)
        accent_help.setStyleSheet("color: #8d9bb1;")

        self.accent_button = QPushButton("Choose accent color")
        self.accent_button.setMaximumWidth(220)
        self.accent_button.clicked.connect(self.choose_accent_color)

        accent_layout.addWidget(accent_label)
        accent_layout.addWidget(accent_help)
        accent_layout.addWidget(self.accent_button)
        settings_layout.addWidget(accent_card)

        settings_layout.addWidget(QLabel(
            "Preferences are stored locally in ~/.config/DeskOps/settings.json"
        ))

        self.reset_settings_button = QPushButton("Restore defaults")
        self.reset_settings_button.setMaximumWidth(220)
        self.reset_settings_button.clicked.connect(self.reset_preferences)
        settings_layout.addWidget(self.reset_settings_button)
        settings_layout.addStretch()

        self.pages.addWidget(settings_page)

        nav_items = [
            ("◈", "Overview"),
            ("▦", "Hardware"),
            ("⌁", "Diagnostics"),
            ("≡", "Reports"),
            ("⚙", "Settings"),
        ]

        self.nav_buttons = []
        for index, (symbol, name) in enumerate(nav_items):
            button = QPushButton(f"   {symbol}     {name}")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(43)
            button.setChecked(index == 0)
            button.clicked.connect(
                lambda checked=False, i=index: self.navigate(i)
            )
            nav.addWidget(button)
            self.nav_buttons.append(button)

        nav.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #253044;")
        nav.addWidget(divider)

        footer_title = QLabel("LOCAL MONITOR")
        footer_title.setStyleSheet(
            "color: #8b9ab2; font-size: 9px; font-weight: 800;"
            " letter-spacing: 1px;"
        )
        footer_status = QLabel("●  Background workers enabled")
        footer_status.setStyleSheet(
            "color: #72d9ae; font-size: 10px; padding-top: 5px;"
        )
        footer_version = QLabel("DESKOPS 0.3 · DEVELOPMENT")
        footer_version.setStyleSheet(
            "color: #526078; font-size: 8px; padding-top: 7px;"
        )

        nav.addWidget(footer_title)
        nav.addWidget(footer_status)
        nav.addWidget(footer_version)

        self.cpu_value = self.overview.cpu_value
        self.mem_value = self.overview.mem_value
        self.disk_value = self.overview.disk_value
        self.cpu_plot = self.overview.cpu_plot
        self.memory_plot = self.overview.memory_plot
        self.cpu_curve = self.overview.cpu_curve
        self.memory_curve = self.overview.memory_curve
        self.status = self.overview.status
        self.process_table = self.overview.process_table
        self.diagnostics_result = self.overview.diagnostics_result

        self.overview.scan_button.clicked.connect(self.run_diagnostics)
        self.overview.export_button.clicked.connect(self.export_report)
        self.overview.refresh_button.clicked.connect(self.refresh_processes)

        main.addWidget(sidebar)
        main.addWidget(self.pages, 1)

        # Cursor de mãozinha em todos os botões da janela.
        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.apply_theme()
        self.apply_accent_color()

        self.refresh_processes()
        self.process_timer.start()
        self.refresh_metrics()
        self.metrics_timer.start()

    def load_preferences(self):
        defaults = {
            "refresh_interval": 2000,
            "accent_color": "#9bb0ff",
            "theme": "dark",
        }
        try:
            with self.settings_path.open("r", encoding="utf-8") as file:
                saved = json.load(file)
            if isinstance(saved, dict):
                interval = int(saved.get("refresh_interval", 2000))
                color = str(saved.get("accent_color", "#9bb0ff"))
                theme = str(saved.get("theme", "dark")).lower()

                if 1000 <= interval <= 10000 and interval % 1000 == 0:
                    defaults["refresh_interval"] = interval
                if QColor(color).isValid():
                    defaults["accent_color"] = color
                if theme in ("dark", "light", "system"):
                    defaults["theme"] = theme
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
        return defaults

    def save_preferences(self):
        self.preferences = {
            "refresh_interval": self.refresh_interval,
            "accent_color": self.accent_color,
            "theme": self.theme_mode,
        }
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with self.settings_path.open("w", encoding="utf-8") as file:
                json.dump(self.preferences, file, indent=2)
        except OSError as error:
            QMessageBox.warning(
                self, "Settings not saved",
                f"Could not save preferences:\n{error}",
            )

    def change_refresh_interval(self, seconds):
        self.refresh_interval = seconds * 1000
        self.process_timer.setInterval(self.refresh_interval)
        self.metrics_timer.setInterval(self.refresh_interval)
        self.save_preferences()

    def choose_accent_color(self):
        color = QColorDialog.getColor(
            QColor(self.accent_color), self, "Choose accent color"
        )
        if color.isValid():
            self.accent_color = color.name()
            self.apply_accent_color()
            self.save_preferences()

    def change_theme(self, mode):
        mode = mode.lower()
        if mode not in ("dark", "light", "system"):
            return
        self.theme_mode = mode
        self.apply_theme()
        self.apply_accent_color()
        self.save_preferences()

    def _theme_stylesheet(self, source, light):
        if not light:
            return source

        replacements = {
            "#0c1018": "#f4f6fa",
            "#101620": "#e9edf4",
            "#151a24": "#ffffff",
            "#141b27": "#ffffff",
            "#273247": "#d7dee8",
            "#29364a": "#d7dee8",
            "#253044": "#d7dee8",
            "#192334": "#e8edf5",
            "#e7edf8": "#1c2636",
            "#f0f4ff": "#172033",
            "#8d9bb1": "#5f6b7b",
            "#91a2bd": "#566477",
            "#dce5f5": "#253247",
            "#edf2fc": "#1c2636",
            "#8592a8": "#5f6b7b",
            "#202a3b": "#e9eef6",
            "#171d28": "#ffffff",
            "#1b2230": "#f3f5f8",
            "#111824": "#ffffff",
            "#1a2434": "#e9eef6",
            "#dce4f2": "#253247",
            "#354055": "#d5dce7",
            "#202735": "#e9edf4",
            "#293345": "#d5dce7",
            "#d1d9e7": "#263244",
            "#151b26": "#ffffff",
            "#11151d": "#f4f6fa",
            "#394357": "#b8c2d1",
            "#e5eaf3": "#1c2636",
            "#94a1b7": "#566477",
            "#e8efff": "#172033",
            "#202d47": "#e8edf5",
            "#34476d": "#c2cddd",
            "#aab6ca": "#566477",
            "#929db1": "#69778c",
            "#9eabc0": "#566477",
            "#526078": "#667085",
            "#66758e": "#69778c",
            "#72819a": "#69778c",
            "#8e9aaf": "#667085",
            "#a5b4fc": "#465fd5",
        }
        for old, new in replacements.items():
            source = source.replace(old, new)
        return source

    def apply_theme(self):
        app = QApplication.instance()
        if app is None:
            return

        if self.theme_mode == "system":
            system_color = app.palette().color(QPalette.ColorRole.Window)
            light = system_color.lightness() >= 128
        else:
            light = self.theme_mode == "light"

        # Theme the application's shared stylesheet.
        app.setStyleSheet(self._theme_stylesheet(STYLE, light))

        # Preserve each widget's original stylesheet so switching back
        # to dark does not repeatedly transform already transformed colors.
        for widget in [self, *self.findChildren(QWidget)]:
            if not widget.property("_deskops_style_saved"):
                widget.setProperty(
                    "_deskops_original_style", widget.styleSheet()
                )
                widget.setProperty("_deskops_style_saved", True)

            original = widget.property("_deskops_original_style") or ""
            widget.setStyleSheet(
                self._theme_stylesheet(original, light)
            )

        # PyQtGraph plots have their own canvas backgrounds.
        plot_background = "#ffffff" if light else "#0c1018"
        for name in ("cpu_plot", "memory_plot"):
            plot = getattr(self, name, None)
            if plot is not None:
                plot.setBackground(plot_background)

    def apply_accent_color(self):
        color = self.accent_color
        qcolor = QColor(color)
        foreground = (
            "#101624" if qcolor.lightness() > 155 else "#ffffff"
        )

        self.brand_mark.setStyleSheet(
            f"color: {foreground}; background-color: {color};"
            " border-radius: 11px; font-size: 22px; font-weight: 900;"
        )

        for button in getattr(self, "nav_buttons", []):
            button.setStyleSheet(
                "QPushButton#navButton {"
                " background: transparent; border: 1px solid transparent;"
                " border-radius: 9px; padding: 12px 13px;"
                " text-align: left; font-size: 12px; font-weight: 600; }"
                "QPushButton#navButton:checked {"
                f" background-color: {color}; color: {foreground};"
                f" border: 1px solid {color}; }}"
            )

        if hasattr(self, "accent_button"):
            self.accent_button.setStyleSheet(
                f"QPushButton {{ background-color: {color};"
                f" color: {foreground}; border: 1px solid {color};"
                " border-radius: 7px; padding: 9px;"
                " font-weight: 700; }"
            )

    def reset_preferences(self):
        self.refresh_interval = 2000
        self.accent_color = "#9bb0ff"
        self.theme_mode = "dark"

        self.interval_spin.blockSignals(True)
        self.interval_spin.setValue(2)
        self.interval_spin.blockSignals(False)

        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText("Dark")
        self.theme_combo.blockSignals(False)

        self.process_timer.setInterval(self.refresh_interval)
        self.metrics_timer.setInterval(self.refresh_interval)
        self.apply_theme()
        self.apply_accent_color()
        self.save_preferences()

    def navigate(self, index):
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)
            for i, button in enumerate(self.nav_buttons):
                button.setChecked(i == index)
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def run_diagnostics(self):
        self.refresh_diagnostics()


    def on_diagnostics_error(self, message):
        self.diagnostics_running = False
        self.status.setText("●  SCAN FAILED")
        self.secondary_report_label.setText(
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
        self.status.setText("●  SCANNING")

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

        self.status.setText("●  MONITORING")


    def on_processes_error(self, message):
        self.process_scan_running = False
        self.status.setText("●  PROCESS ERROR")
        self.secondary_report_label.setText(
            f"Could not inspect processes: {message}"
        )


    def refresh_metrics(self):
        if getattr(self, "metrics_running", False):
            return

        self.metrics_running = True

        worker = MetricsWorker()
        worker.signals.finished.connect(
            self.on_metrics_ready
        )
        worker.signals.error.connect(
            self.on_metrics_error
        )

        self.thread_pool.start(worker)

    def on_metrics_ready(self, metrics):
        self.metrics_running = False

        self.cpu_value.setText(
            f'{metrics["cpu_percent"]:.0f}%'
        )
        self.mem_value.setText(
            f'{metrics["memory_percent"]:.0f}%'
        )
        self.disk_value.setText(
            f'{metrics["root_disk_percent"]:.0f}%'
        )

        self.cpu_history.append(
            float(metrics["cpu_percent"])
        )
        self.memory_history.append(
            float(metrics["memory_percent"])
        )

        samples = list(range(len(self.cpu_history)))

        self.cpu_curve.setData(
            samples, list(self.cpu_history)
        )
        self.memory_curve.setData(
            samples, list(self.memory_history)
        )

    def on_metrics_error(self, message):
        self.metrics_running = False
        self.status.setText("●  METRICS ERROR")

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

        warnings = [
            alert for alert in report["alerts"]
            if alert["level"] == "warning"
        ]

        heading = (
            f"Diagnostics complete — {len(warnings)} warning(s) found."
            if warnings else
            "Diagnostics complete — no warnings found."
        )

        details = "\n".join(
            f'• {alert["message"]}'
            for alert in report["alerts"]
        )

        timestamp = report.get("generated_at", "")
        timestamp = timestamp[:19].replace("T", " ")

        self.diagnostics_result.setText(
            f"{heading}\n"
            f"{details}\n"
            f'CPU: {metrics["cpu_percent"]:.1f}% | '
            f'RAM: {metrics["memory_percent"]:.1f}% | '
            f'Disk: {metrics["root_disk_percent"]:.1f}%\n'
            f'Uptime: {metrics["uptime_hours"]} hours | '
            f'Last check: {timestamp}'
        )

        system = report.get("system", {})
        memory_total = metrics.get("memory_total_bytes", 0)
        memory_available = metrics.get("memory_available_bytes", 0)
        disk_total = metrics.get("root_disk_total_bytes", 0)
        disk_free = metrics.get("root_disk_free_bytes", 0)

        def gib(value):
            return f"{value / (1024 ** 3):.2f} GiB"

        cpu = metrics.get("cpu_percent", 0)
        ram = metrics.get("memory_percent", 0)
        disk = metrics.get("root_disk_percent", 0)
        uptime = metrics.get("uptime_hours", 0)

        warnings = [
            alert for alert in report.get("alerts", [])
            if alert.get("level", "").lower() == "warning"
        ]

        if cpu >= 90:
            cpu_status = "HIGH — processor usage may affect responsiveness."
        elif cpu >= 70:
            cpu_status = "ELEVATED — check again during normal use."
        else:
            cpu_status = "NORMAL — no high CPU usage detected in this sample."

        if ram >= 90:
            ram_status = "HIGH — available memory is critically limited."
        elif ram >= 75:
            ram_status = "ELEVATED — monitor memory consumption."
        else:
            ram_status = "NORMAL — memory usage is below the warning threshold."

        if disk >= 90:
            disk_status = "HIGH — the root filesystem is nearly full."
        elif disk >= 75:
            disk_status = "ELEVATED — keep an eye on available disk space."
        else:
            disk_status = "NORMAL — root filesystem usage is below the warning threshold."

        generated_at = report.get("generated_at", "Unknown")
        generated_at = generated_at.replace("T", " ")[:19]

        lines = [
            "DESKOPS — SYSTEM DIAGNOSTICS",
            "=" * 42,
            "SCAN SUMMARY",
            "-" * 42,
            (
                f"Result: {len(warnings)} warning(s) found."
                if warnings else
                "Result: No automatic warnings found."
            ),
            f"Generated at: {generated_at}",
            "",
            "RESOURCE USAGE",
            "-" * 42,
            f"CPU:  {cpu:.1f}% — {cpu_status}",
            f"RAM:  {ram:.1f}% used",
            f"      Total: {gib(memory_total)}",
            f"      Available: {gib(memory_available)}",
            f"      Used: {gib(max(0, memory_total - memory_available))}",
            f"      Assessment: {ram_status}",
            f"Root filesystem: {disk:.1f}% used",
            f"      Total: {gib(disk_total)}",
            f"      Free: {gib(disk_free)}",
            f"      Used: {gib(max(0, disk_total - disk_free))}",
            f"      Assessment: {disk_status}",
            f"System uptime: {uptime} hour(s)",
            "",
            "SYSTEM INFORMATION",
            "-" * 42,
            f"Operating system: {system.get('os', 'Unknown')}",
            f"Platform: {system.get('distribution', 'Unknown')}",
            f"Kernel: {system.get('kernel', 'Unknown')}",
            f"Architecture: {system.get('architecture', 'Unknown')}",
            f"Python version: {system.get('python_version', 'Unknown')}",
            "",
            "FINDINGS & ALERTS",
            "-" * 42,
        ]

        alerts = report.get("alerts", [])
        if alerts:
            for index, alert in enumerate(alerts, start=1):
                level = alert.get("level", "info").upper()
                message = alert.get("message", "No details available")
                lines.append(f"{index}. [{level}] {message}")
        else:
            lines.append("No findings were returned by the automatic checks.")

        lines.extend([
            "",
            "RECOMMENDED NEXT STEPS",
            "-" * 42,
        ])

        recommendations = []

        if cpu >= 70:
            recommendations.append(
                "Check the Overview process list for applications "
                "using significant CPU resources."
            )
        if ram >= 75:
            recommendations.append(
                "Close applications and browser tabs you do not need, "
                "then check memory usage again."
            )
        if disk >= 75:
            recommendations.append(
                "Review disk usage and remove only files you no longer "
                "need if storage space is running low."
            )
        if not recommendations:
            recommendations.append(
                "No resource-specific action is indicated by these "
                "basic thresholds. Continue monitoring during normal use."
            )

        for index, recommendation in enumerate(recommendations, start=1):
            lines.append(f"{index}. {recommendation}")

        lines.extend([
            "",
            "SCOPE & LIMITATIONS",
            "-" * 42,
            "This report summarizes the metrics collected during this scan.",
            "It does not perform hardware stress tests, temperature checks,",
            "SMART disk health checks, or system-log analysis.",
            "A clean result does not guarantee that every component is healthy.",
        ])

        text_report = "\n".join(lines)

        self.secondary_report_label.setTextFormat(
            Qt.TextFormat.PlainText
        )
        self.secondary_report_label.setWordWrap(True)
        self.secondary_report_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.secondary_report_label.setText(text_report)
        self.secondary_report_label.setMinimumHeight(600)
        self.secondary_report_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.reports_status_label.setText(
            f"Report available · {timestamp}"
        )
        self.status.setText("●  SCAN COMPLETE")

        self.cpu_history.append(float(metrics["cpu_percent"]))
        self.memory_history.append(float(metrics["memory_percent"]))

        samples = list(range(len(self.cpu_history)))
        self.cpu_curve.setData(samples, list(self.cpu_history))
        self.memory_curve.setData(samples, list(self.memory_history))



def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    # Allow Ctrl+C to stop the Qt event loop.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal_timer = QTimer(app)
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(200)

    window = DeskOps()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

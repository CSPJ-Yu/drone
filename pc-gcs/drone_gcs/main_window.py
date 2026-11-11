from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from drone_gcs.horizon import ArtificialHorizon
from drone_gcs.camera_widget import CameraWidget
from drone_gcs.synchronization import TelemetryHistory
from drone_gcs.yolo_widget import YoloWidget
from drone_gcs.map_widget import MapWidget
from drone_gcs.network import get_local_ipv4, gps_fix_label
from drone_gcs.telemetry import TelemetryState, TelemetryWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Drone GCS v0.2")
        self.resize(1280, 800)

        self.history = TelemetryHistory()
        self._build_ui()
        self._apply_theme()

        self.worker = TelemetryWorker(history=self.history)
        self.worker.telemetry.connect(self._update_telemetry)
        self.worker.connection_changed.connect(self._update_connection)
        self.worker.status_text.connect(self._update_status_text)
        self.worker.start()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()

        title = QLabel("DRONE GCS")
        title.setObjectName("title")

        subtitle = QLabel("GROUND CONTROL STATION  /  v0.2")
        subtitle.setObjectName("subtitle")

        title_box = QVBoxLayout()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.connection_dot = QLabel("●")
        self.connection_dot.setObjectName("offlineDot")

        self.connection_label = QLabel("WAITING FOR MAVLINK")
        self.connection_label.setObjectName("connection")

        header.addWidget(self.connection_dot)
        header.addWidget(self.connection_label)

        layout.addLayout(header)

        # Warning banner
        self.warning_label = QLabel("WAITING FOR TELEMETRY")
        self.warning_label.setObjectName("warning")
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)

        # Main content
        content = QHBoxLayout()
        content.setSpacing(16)

        displays = QTabWidget()
        displays.setObjectName("displays")

        self.horizon = ArtificialHorizon()
        self.horizon.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.map_widget = MapWidget()
        self.camera_widget = CameraWidget(history=self.history)
        self.yolo_widget = YoloWidget()

        self.camera_widget.frame_ready.connect(
            self.yolo_widget.submit
        )

        displays.addTab(self.horizon, "ATTITUDE")
        displays.addTab(self.map_widget, "MAP")
        displays.addTab(self.camera_widget, "CAMERA")
        displays.addTab(self.yolo_widget, "YOLO")

        content.addWidget(displays, 3)

        # Flight panel
        panel = QFrame()
        panel.setObjectName("panel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)

        panel_layout.addWidget(self._section_label("FLIGHT"))

        grid = QGridLayout()
        grid.setVerticalSpacing(10)

        self.mode_value = self._value_label("UNKNOWN")
        self.armed_value = self._value_label("UNKNOWN")

        self.roll_value = self._value_label("--")
        self.pitch_value = self._value_label("--")
        self.yaw_value = self._value_label("--")

        self.satellites_value = self._value_label("--")
        self.gps_fix_value = self._value_label("--")

        self.latitude_value = self._value_label("--")
        self.longitude_value = self._value_label("--")
        self.altitude_value = self._value_label("--")
        self.relative_altitude_value = self._value_label("--")

        self.battery_voltage_value = self._value_label("--")
        self.battery_current_value = self._value_label("--")
        self.battery_remaining_value = self._value_label("--")

        self.gps_accuracy_value = self._value_label("--")

        rows = [
            ("Mode", self.mode_value),
            ("Armed", self.armed_value),
            ("Roll", self.roll_value),
            ("Pitch", self.pitch_value),
            ("Yaw", self.yaw_value),
            ("Satellites", self.satellites_value),
            ("GPS Fix", self.gps_fix_value),
            ("Latitude", self.latitude_value),
            ("Longitude", self.longitude_value),
            ("Altitude", self.altitude_value),
            ("Relative Alt", self.relative_altitude_value),
            ("Battery", self.battery_voltage_value),
            ("Current", self.battery_current_value),
            ("Remaining", self.battery_remaining_value),
            ("GPS Accuracy", self.gps_accuracy_value),
        ]

        for row, (name, value) in enumerate(rows):
            key = QLabel(name.upper())
            key.setObjectName("key")

            grid.addWidget(key, row, 0)
            grid.addWidget(
                value,
                row,
                1,
                alignment=Qt.AlignRight,
            )

        panel_layout.addLayout(grid)
        panel_layout.addStretch()

        local_ip = get_local_ipv4()

        self.endpoint_label = QLabel(
            f"PC IP  •  {local_ip}\nUDP PORT  •  14550"
        )
        self.endpoint_label.setObjectName("endpoint")

        panel_layout.addWidget(self.endpoint_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(310)

        content.addWidget(scroll, 2)

        layout.addLayout(content, 1)

        self.setCentralWidget(root)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        return label

    @staticmethod
    def _value_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("value")
        label.setFont(QFont("Menlo", 13, QFont.Bold))
        return label

    def _update_telemetry(self, state: TelemetryState) -> None:
        # Ignore telemetry snapshots without a valid heartbeat.
        if state.heartbeat_at is None:
            return

        self.mode_value.setText(state.mode)

        if state.armed is None:
            armed_text = "UNKNOWN"
            armed_property = "unknown"
        else:
            armed_text = "YES" if state.armed else "NO"
            armed_property = "true" if state.armed else "false"

        self.armed_value.setText(armed_text)
        self.armed_value.setProperty("armed", armed_property)
        self.armed_value.style().unpolish(self.armed_value)
        self.armed_value.style().polish(self.armed_value)

        if state.attitude_at is not None:
            self.roll_value.setText(f"{state.roll:+.2f}°")
            self.pitch_value.setText(f"{state.pitch:+.2f}°")
            self.yaw_value.setText(f"{state.yaw:.2f}°")
            self.horizon.set_attitude(state.roll, state.pitch)

        self.satellites_value.setText(
            "N/A" if state.satellites is None
            else str(state.satellites)
        )

        self.gps_fix_value.setText(
            gps_fix_label(state.gps_fix)
        )

        if state.latitude is not None and state.longitude is not None:
            self.latitude_value.setText(
                f"{state.latitude:.7f}°"
            )
            self.longitude_value.setText(
                f"{state.longitude:.7f}°"
            )

            if state.altitude is not None:
                self.altitude_value.setText(
                    f"{state.altitude:.1f} m"
                )

            self.map_widget.update_position(
                state.latitude,
                state.longitude,
                state.altitude or 0.0,
                state.satellites,
                gps_fix_label(state.gps_fix),
            )

        self.relative_altitude_value.setText(
            "N/A" if state.relative_altitude is None
            else f"{state.relative_altitude:.1f} m"
        )

        self.battery_voltage_value.setText(
            "N/A" if state.battery_voltage is None
            else f"{state.battery_voltage:.2f} V"
        )

        self.battery_current_value.setText(
            "N/A" if state.battery_current is None
            else f"{state.battery_current:.2f} A"
        )

        self.battery_remaining_value.setText(
            "N/A" if state.battery_remaining is None
            else f"{state.battery_remaining}%"
        )

        self.gps_accuracy_value.setText(
            "N/A" if state.gps_accuracy is None
            else f"{state.gps_accuracy:.2f} m"
        )

    def _update_connection(
        self,
        connected: bool,
        message: str,
    ) -> None:
        self.connection_label.setText(message)

        self.connection_dot.setObjectName(
            "onlineDot" if connected else "offlineDot"
        )
        self.connection_dot.style().unpolish(self.connection_dot)
        self.connection_dot.style().polish(self.connection_dot)

        if not connected:
            labels = [
                self.mode_value,
                self.armed_value,
                self.roll_value,
                self.pitch_value,
                self.yaw_value,
                self.satellites_value,
                self.gps_fix_value,
                self.latitude_value,
                self.longitude_value,
                self.altitude_value,
                self.relative_altitude_value,
                self.battery_voltage_value,
                self.battery_current_value,
                self.battery_remaining_value,
                self.gps_accuracy_value,
            ]

            for label in labels:
                label.setText("--")

            self.mode_value.setText("UNKNOWN")
            self.armed_value.setText("UNKNOWN")
            self.armed_value.setProperty("armed", "unknown")
            self.armed_value.style().unpolish(self.armed_value)
            self.armed_value.style().polish(self.armed_value)

            self.warning_label.setText(
                f"TELEMETRY UNAVAILABLE: {message}"
            )
        else:
            self.warning_label.setText(
                "CONNECTED / NO RECENT WARNINGS"
            )

    def _update_status_text(
        self,
        severity: int,
        message: str,
    ) -> None:
        if not message:
            return

        self.warning_label.setText(
            f"[SEVERITY {severity}] {message}"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.worker.stop()
        self.worker.wait(1500)
        event.accept()

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #07101d;
                color: #e9f0f8;
            }

            #title {
                font: 700 25px 'Helvetica Neue';
                letter-spacing: 2px;
            }

            #subtitle, #endpoint {
                color: #6f829a;
                font: 10px 'Helvetica Neue';
            }

            #connection {
                color: #b7c5d6;
                font: 700 11px 'Helvetica Neue';
            }

            #onlineDot {
                color: #2ce6a6;
                font-size: 20px;
            }

            #offlineDot {
                color: #ff5c6c;
                font-size: 20px;
            }

            #warning {
                background: #34202b;
                border: 1px solid #8e4c5d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffb6bf;
                font-weight: 700;
            }

            #panel {
                background: #0d1929;
                border: 1px solid #26384d;
                border-radius: 12px;
            }

            #displays::pane {
                border: 1px solid #26384d;
                border-radius: 10px;
            }

            QTabBar::tab {
                background: #0d1929;
                color: #778aa2;
                padding: 9px 20px;
            }

            QTabBar::tab:selected {
                background: #17304a;
                color: #5cc8ff;
            }

            QLineEdit {
                background: #07101d;
                border: 1px solid #314761;
                border-radius: 4px;
                padding: 7px;
                color: #e9f0f8;
            }

            QPushButton {
                background: #17304a;
                border: 1px solid #3b759d;
                border-radius: 4px;
                padding: 7px 14px;
                color: #5cc8ff;
                font-weight: 700;
            }

            QPushButton:hover {
                background: #214565;
            }

            #section {
                color: #5cc8ff;
                font: 700 12px 'Helvetica Neue';
                letter-spacing: 2px;
                margin-bottom: 12px;
            }

            #key {
                color: #778aa2;
                font: 700 10px 'Helvetica Neue';
            }

            #value {
                color: #f4f8fc;
            }

            #value[armed="true"] {
                color: #ff6676;
            }

            #value[armed="false"] {
                color: #2ce6a6;
            }
        """)
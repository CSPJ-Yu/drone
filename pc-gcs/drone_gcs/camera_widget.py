"""Decode live MPEG-TS without a media player's presentation queue."""
import threading
import time

import av
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from drone_gcs.synchronization import TelemetryHistory, describe


class VideoReceiver(threading.Thread):
    def __init__(self, port, history=None):
        super().__init__(daemon=True)
        self.port = port
        self.history = history if history is not None else TelemetryHistory()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.last_frame = 0.0
        self.error = ''
        self.count = 0

    def run(self):
        while not self.stop_event.is_set():
            try:
                with av.open(
                    f'udp://0.0.0.0:{self.port}?fifo_size=2048&overrun_nonfatal=1',
                    format='mpegts', timeout=(3.0, 2.0),
                    options={'probesize': '32768', 'analyzeduration': '100000',
                             'flags': 'low_delay'},
                ) as container:
                    stream = container.streams.video[0]
                    stream.codec_context.thread_count = 1
                    for packet in container.demux(stream):
                        if self.stop_event.is_set():
                            return
                        try:
                            frames = packet.decode()
                        except av.error.InvalidDataError:
                            continue
                        for frame in frames:
                            available_at = time.monotonic()
                            rgb = frame.reformat(format='rgb24')
                            plane = rgb.planes[0]
                            picture = QImage(bytes(plane), rgb.width, rgb.height,
                                             plane.line_size, QImage.Format_RGB888).copy()
                            with self.lock:
                                self.latest = self.history.frame(picture, self.count + 1, available_at)
                                self.last_frame = available_at
                                self.count += 1
                                self.error = ''
            except Exception as exc:
                with self.lock:
                    self.error = str(exc)
            self.stop_event.wait(0.3)


class CameraWidget(QWidget):
    frame_ready = Signal(object)
    def __init__(self, history=None):
        super().__init__()
        self.receiver = None
        self.history = history if history is not None else TelemetryHistory()
        self.pending_port = None
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('UDP VIDEO PORT'))
        self.port = QLineEdit('5600')
        self.port.setMaximumWidth(90)
        controls.addWidget(self.port)
        self.connect_button = QPushButton('LISTEN')
        self.connect_button.clicked.connect(self.start_listening)
        controls.addWidget(self.connect_button)
        self.status = QLabel('WAITING')
        controls.addWidget(self.status, 1)
        layout.addLayout(controls)
        self.video = QLabel('Waiting for UDP video')
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(160, 120)
        self.video.setStyleSheet('background: #050a11; color: #e9f0f8;')
        self.video.setScaledContents(False)
        from PySide6.QtWidgets import QSizePolicy
        self.video.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.video, 1)
        self.sync_label = QLabel('Waiting for frame / MAVLink')
        self.sync_label.setWordWrap(True)
        layout.addWidget(self.sync_label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(33)
        QApplication.instance().aboutToQuit.connect(self.shutdown)
        self.start_listening()

    def start_listening(self):
        try:
            port = int(self.port.text())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            self.status.setText('INVALID PORT')
            return
        self.pending_port = port
        if self.receiver:
            self.receiver.stop_event.set()
        self.status.setText('CONNECTING')

    def refresh(self):
        if self.pending_port is not None:
            if self.receiver and self.receiver.is_alive():
                return
            self.receiver = VideoReceiver(self.pending_port, self.history)
            self.pending_port = None
            self.receiver.start()
        if not self.receiver:
            return
        with self.receiver.lock:
            picture = self.receiver.latest
            self.receiver.latest = None
            age = time.monotonic() - self.receiver.last_frame
            error = self.receiver.error
        if picture is not None:
            self.frame_ready.emit(picture)
            self.sync_label.setText(describe(picture.context))
            self.video.setPixmap(QPixmap.fromImage(picture.image).scaled(
                self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.status.setText('VIDEO ONLINE' if age < 1.0 else 'WAITING / RECONNECTING')
        self.status.setToolTip(error)

    def shutdown(self):
        self.timer.stop()
        self.pending_port = None
        if self.receiver:
            self.receiver.stop_event.set()
            self.receiver.join(timeout=4.0)

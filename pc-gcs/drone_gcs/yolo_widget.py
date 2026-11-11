"""Latest-frame-only YOLO inference, sharing the CAMERA UDP receiver."""
import threading
import time
from pathlib import Path
from drone_gcs.synchronization import describe

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QSizePolicy

MODEL_PATH = Path(__file__).resolve().parents[1] / 'models' / 'yolo11s.pt'
MODEL_LABEL = 'YOLO11s'


class Detector(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.condition = threading.Condition()
        self.stopping = False
        self.pending = None
        self.output = None
        self.status = f'LOADING {MODEL_LABEL}'
        self.error = ''
        self.processed = 0

    def submit(self, image):
        with self.condition:
            self.pending = image
            self.condition.notify()

    def stop(self):
        with self.condition:
            self.stopping = True
            self.pending = None
            self.condition.notify()

    def run(self):
        try:
            import numpy as np
            import torch
            from ultralytics import YOLO
            if not MODEL_PATH.is_file():
                raise FileNotFoundError(f'Model missing: {MODEL_PATH}')
            torch.set_num_threads(2)
            device = 0 if torch.cuda.is_available() else 'cpu'
            device_label = ('GPU: ' + torch.cuda.get_device_name(0)) if device == 0 else 'CPU'
            model = YOLO(str(MODEL_PATH))
            with self.condition:
                self.status = f'{MODEL_LABEL} / {device_label} / WAITING FOR CAMERA'
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.stopping or self.pending is not None)
                    if self.stopping:
                        return
                    envelope = self.pending
                    self.pending = None
                started = time.monotonic()
                image = envelope.image.convertToFormat(QImage.Format_RGB888)
                rgb = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(
                    image.height(), image.bytesPerLine())[:, :image.width()*3].reshape(
                    image.height(), image.width(), 3)
                result = model.predict(rgb[:, :, ::-1].copy(), imgsz=416, conf=0.35,
                                       device=device, verbose=False)[0]
                plotted = result.plot()[:, :, ::-1].copy()
                output = QImage(plotted.data, plotted.shape[1], plotted.shape[0],
                                plotted.strides[0], QImage.Format_RGB888).copy()
                duration = time.monotonic() - started
                with self.condition:
                    if self.stopping:
                        return
                    self.processed += 1
                    self.output = (output, envelope.context)
                    self.status = (f'{MODEL_LABEL} / {device_label} | {len(result.boxes)} objects | '
                                   f'{duration*1000:.0f} ms inference')
        except Exception as exc:
            with self.condition:
                self.error = str(exc)
                self.status = 'YOLO ERROR (see tooltip)'


class YoloWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.detector = None
        self.enabled = True
        self.last_input = 0.0
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.status = QLabel(f'{MODEL_LABEL} / select YOLO tab to start')
        self.status.setWordWrap(True)
        controls.addWidget(self.status, 1)
        self.button = QPushButton('PAUSE')
        self.button.clicked.connect(self.toggle)
        controls.addWidget(self.button)
        layout.addLayout(controls)
        self.video = QLabel('Waiting for camera')
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(160, 120)
        self.video.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.video, 1)
        self.sync_label = QLabel('Waiting for synchronized frame')
        self.sync_label.setWordWrap(True)
        layout.addWidget(self.sync_label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(50)
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def submit(self, image):
        self.last_input = time.monotonic()
        if self.enabled and self.isVisible():
            if self.detector is None:
                self.detector = Detector()
                self.detector.start()
            self.detector.submit(image)

    def toggle(self):
        self.enabled = not self.enabled
        self.button.setText('PAUSE' if self.enabled else 'RESUME')

    def refresh(self):
        if not self.enabled:
            self.status.setText('PAUSED')
            return
        if time.monotonic() - self.last_input > 2:
            self.status.setText('WAITING FOR CAMERA / SIGNAL LOST')
            return
        if self.detector:
            with self.detector.condition:
                output = self.detector.output
                self.detector.output = None
                status, error = self.detector.status, self.detector.error
            self.status.setText(status)
            self.status.setToolTip(error)
            if output is not None:
                image, context = output
                self.sync_label.setText(describe(context))
                self.video.setPixmap(QPixmap.fromImage(image).scaled(
                    self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def shutdown(self):
        self.timer.stop()
        if self.detector:
            self.detector.stop()
            self.detector.join(timeout=5)

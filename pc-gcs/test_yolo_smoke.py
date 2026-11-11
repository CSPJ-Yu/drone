"""Manual smoke check: real model inference and offscreen annotated display."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
import torch
from ultralytics.utils import ASSETS
from drone_gcs.yolo_widget import YoloWidget
from drone_gcs.synchronization import TelemetryHistory


def main():
    app = QApplication([])
    widget = YoloWidget()
    widget.show()
    app.processEvents()
    picture = QImage(str(ASSETS / 'bus.jpg'))
    assert not picture.isNull()
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            widget.submit(TelemetryHistory().frame(picture, 1, time.monotonic()))
            app.processEvents()
            time.sleep(.07)
            if widget.detector.error or widget.detector.processed >= 10:
                break
        assert widget.detector.processed >= 10, widget.detector.error
        widget.refresh()
        assert not widget.video.pixmap().isNull()
        print(widget.detector.status)
        print('CUDA available:', torch.cuda.is_available())
        if torch.cuda.is_available():
            assert 'GPU:' in widget.detector.status
        print('PASS: repeated inference and annotated display')
    finally:
        widget.shutdown()
        assert not widget.detector.is_alive()


if __name__ == '__main__':
    main()

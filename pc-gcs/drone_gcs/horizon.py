from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class ArtificialHorizon(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.roll = 0.0
        self.pitch = 0.0
        self.setMinimumSize(440, 330)

    def set_attitude(self, roll: float, pitch: float) -> None:
        self.roll = roll
        self.pitch = pitch
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#08111f"))

        painter.save()
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(-self.roll)
        pitch_offset = max(-45.0, min(45.0, self.pitch)) * 4.0
        painter.translate(0, pitch_offset)

        span = self.width() * 2
        painter.fillRect(-span, -span, span * 2, span, QColor("#2b78b8"))
        painter.fillRect(-span, 0, span * 2, span, QColor("#8b5a2b"))
        painter.setPen(QPen(QColor("white"), 3))
        painter.drawLine(-span, 0, span, 0)

        painter.setFont(QFont("Segoe UI", 9))
        for degrees in range(-30, 31, 10):
            if degrees == 0:
                continue
            y = -degrees * 4
            half_width = 42 if degrees % 20 else 65
            painter.drawLine(-half_width, y, half_width, y)
            painter.drawText(half_width + 8, y + 4, str(degrees))
            painter.drawText(-half_width - 28, y + 4, str(degrees))
        painter.restore()

        center_x, center_y = self.width() / 2, self.height() / 2
        painter.setPen(QPen(QColor("#ffcf33"), 4))
        painter.drawLine(int(center_x - 75), int(center_y), int(center_x - 18), int(center_y))
        painter.drawLine(int(center_x + 18), int(center_y), int(center_x + 75), int(center_y))
        painter.drawLine(int(center_x), int(center_y - 8), int(center_x), int(center_y + 12))
        painter.setBrush(QColor("#ffcf33"))
        painter.drawPolygon(QPolygonF([
            QPointF(center_x - 8, center_y),
            QPointF(center_x + 8, center_y),
            QPointF(center_x, center_y + 10),
        ]))

        painter.setPen(QPen(QColor("#41536b"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 12, 12)

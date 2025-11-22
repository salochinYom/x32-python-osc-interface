import sys
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QVBoxLayout,
    QSlider,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtCore import QPoint
from PySide6.QtGui import QFont


class TouchSlider(QSlider):
    """Slider subclass that accepts presses anywhere and supports
    vertical swipes to change the value relative to the start position.
    Moved to top-level so it can be reused and tested more easily.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_pos = None
        self._start_value = None

    def _value_from_pos(self, pos: QPoint) -> int:
        # Map a QPoint (pos) in widget coordinates to a slider value
        minimum, maximum = self.minimum(), self.maximum()
        if self.orientation() == Qt.Horizontal:
            w = max(1, self.width())
            x = min(max(0, pos.x()), w)
            frac = x / w
            return int(minimum + frac * (maximum - minimum))
        else:
            h = max(1, self.height())
            y = min(max(0, pos.y()), h)
            # vertical slider: top => maximum
            frac = 1.0 - (y / h)
            return int(minimum + frac * (maximum - minimum))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos = event.pos()
            self._start_value = self.value()
            # set immediate value from the pressed position
            try:
                self.setValue(self._value_from_pos(event.pos()))
            except Exception:
                pass
            self.setSliderDown(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._start_pos is None:
            super().mouseMoveEvent(event)
            return
        dx = event.pos().x() - self._start_pos.x()
        dy = event.pos().y() - self._start_pos.y()
        # Choose dominant direction: horizontal moves use x, vertical uses dy
        if abs(dx) >= abs(dy):
            val = self._value_from_pos(event.pos())
        else:
            # map vertical drag to value change relative to start
            vrange = self.maximum() - self.minimum()
            fraction = -dy / max(1, self.height())
            val = int(self._start_value + fraction * vrange)
        val = max(self.minimum(), min(self.maximum(), val))
        self.setValue(val)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._start_pos = None
        self._start_value = None
        self.setSliderDown(False)
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        self.label = QLabel(text="ch09")
        # larger label font for visibility
        self.label.setStyleSheet("font-size: 36px; font-weight: 300;")


        # use the top-level TouchSlider which accepts touches anywhere
        # and supports vertical swipes to change the value when the
        # user drags up/down.
        self.slider = TouchSlider()
        #self.slider = QSlider()
        self.slider.setTracking(True)



        # touch-friendly visuals: much larger groove + very large handle
        self.slider.setStyleSheet("""
        QSlider::groove:horizontal {
            height: 64px;
            background: #e6e6e6;
            border-radius: 32px;
        }
        QSlider::handle:horizontal {
            /* very large handle for easy visibility and touch interaction */
            width: 220px;
            height: 220px;
            /* (groove_height - handle_height) / 2 = (64 - 220) / 2 = -78 */
            margin: -78px 0; /* centers handle on the groove */
            border-radius: 110px;
            background: #333; /* darker for contrast */
            border: 6px solid #111;
        }
        """)
        # increase widget size constraints so the very large handle has room
        self.slider.setMaximumWidth(1400)
        self.slider.setFixedHeight(300)
        self.slider.setMinimumHeight(300)

        layout = QVBoxLayout()
        # make spacing and margins much larger so controls aren't cramped
        layout.setSpacing(48)
        layout.setContentsMargins(80, 80, 80, 80)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        # center widgets horizontally and vertically inside the layout
        layout.setAlignment(Qt.AlignCenter)
        

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

app = QApplication(sys.argv)
# make the application font larger so all widgets scale
app.setFont(QFont("Sans", 36))

window = MainWindow()
#window.show()
window.showFullScreen()

app.exec()
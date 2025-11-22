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

from PySide6.QtCore import QPoint
from PySide6.QtCore import QThread, QObject, Signal, Slot, QTimer

from PySide6.QtWidgets import QPushButton

#stuff for x32
import xair_api


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

    @property
    def manipulating(self) -> bool:
        """True while the user is pressing/dragging the slider."""
        return self._start_pos is not None or self.isSliderDown()


# helpers: map slider (0..100) <-> dB (-90..10) using power curve (gamma)
DB_MIN = -90.0
DB_MAX = 10.0
GAMMA = 0.25  # increase for more fine control at low volumes

def slider_to_db(slider_value: int, slider_min=0, slider_max=100) -> float:
    frac = (slider_value - slider_min) / max(1, (slider_max - slider_min))
    curv = frac ** GAMMA
    return DB_MIN + curv * (DB_MAX - DB_MIN)

def db_to_slider(db_value: float, slider_min=0, slider_max=100) -> int:
    frac = (db_value - DB_MIN) / max(1e-6, (DB_MAX - DB_MIN))
    frac = min(max(frac, 0.0), 1.0)
    inv = frac ** (1.0 / GAMMA)
    return int(round(slider_min + inv * (slider_max - slider_min)))


class MainWindow(QMainWindow):
    def __init__(self, console=None):
        super().__init__()

        self.console = console

        self.setWindowTitle("My App")

        self.label = QLabel(text="strip 8")
        # larger label font for visibility
        self.label.setStyleSheet("font-size: 36px; font-weight: 300;")

        #display for volume of ch09
        self.volume_display = QLabel(text="NAN")
        self.volume_display.setStyleSheet("font-size: 18px; font-weight: 300;")

        # poll mixer every 10 ms (0.01 s) and update volume_display
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(25)  # milliseconds
        self._poll_timer.timeout.connect(self._poll_mixer)
        self._poll_timer.start()


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
        self.slider.setFixedHeight(200)
        #self.slider.setMinimumHeight(300)

        self.slider.valueChanged.connect(self.on_slider_value_changed)

        #button to enable/disable mute
        self.mute_button = QPushButton("Mute")
        self.mute_button.setCheckable(True)

        self.mute_button.toggled.connect(self.on_mute_toggled)
        # make the button larger and show red when checked
        self.mute_button.setStyleSheet("""
        QPushButton {
            font-size: 28px;
            padding: 12px 24px;
            background-color: #444;
            color: #fff;
            border-radius: 8px;
            border: 2px solid #222;
        }

        /* normal hover/pressed for unchecked buttons */
        QPushButton:hover {
            background-color: #555;
        }
        QPushButton:pressed {
            background-color: #333;
        }

        /* checked state */
        QPushButton:checked {
            background-color: #c0392b; /* red when checked */
            color: #fff;
            border-color: #8b1e14;
        }

        /* ensure checked appearance persists while hovered/pressed */
        QPushButton:checked:hover {
            background-color: #b83225; /* slightly darker red on hover */
        }
        QPushButton:checked:pressed {
            background-color: #8b2318; /* even darker when pressed */
        }
        """)

        layout = QVBoxLayout()
        # make spacing and margins much larger so controls aren't cramped
        layout.setSpacing(48)
        layout.setContentsMargins(80, 80, 80, 80)
        layout.addWidget(self.label)
        layout.addWidget(self.volume_display)
        layout.addWidget(self.slider)
        layout.addWidget(self.mute_button)
        # center widgets horizontally and vertically inside the layout
        layout.setAlignment(Qt.AlignCenter)
        

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def on_mute_toggled(self, checked):
        self.console.strip[8].mix.on = not(checked)

    def on_slider_value_changed(self, value):
        db = slider_to_db(value)
        mixer.strip[8].mix.fader = db
        
    def _poll_mixer(self):
        """Called on the main thread via QTimer to update the volume display."""
        try:
            if self.console is None:
                return              
            #update the label with its name
            self.label.setText(self.console.strip[8].config.name)
            # read fader value from mixer and format for display
            fader_val = self.console.strip[8].mix.fader
            # format as needed (two decimals shown here)
            self.volume_display.setText(f"{fader_val:.2f} {self.slider.manipulating}")

            #update slider position if user is not manipulating it
            if not self.slider.manipulating:
                slider_val = db_to_slider(fader_val)
                self.slider.setValue(slider_val)
            
            #update the mute button state
            # checked == True means the UI shows "muted"
            muted = not bool(self.console.strip[8].mix.on)
            self.mute_button.setChecked(muted)
        except Exception:
            # ignore transient errors (connection etc.)
            pass


#do console initialization
ip = "192.168.20.226"
port = 10023
server_port = 10023  # Port your client listens on
kind_id = "X32"

with xair_api.connect(kind_id, ip=ip) as mixer:
    app = QApplication(sys.argv)
    # make the application font larger so all widgets scale
    app.setFont(QFont("Sans", 36))

    window = MainWindow(mixer)
    #window.show()
    window.showFullScreen()
    app.exec()
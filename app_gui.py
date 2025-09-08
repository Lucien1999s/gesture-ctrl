import numpy as np
import cv2
from PySide6 import QtCore, QtGui, QtWidgets
from src.ui.qt_app import GestureEngine, GESTURE_LABELS, ACTION_CHOICES, DEFAULT_BINDINGS

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gesture-ctrl")
        self.resize(1100, 680)

        # ==== Left: camera preview ====
        self.video_label = QtWidgets.QLabel()
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background:#111; border-radius:12px;")

        # ==== Right: settings panel ====
        panel = QtWidgets.QWidget()
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(10)

        # Gesture control toggle (disabled by default)
        self.toggle_active = QtWidgets.QCheckBox("Enable gesture control")
        self.toggle_active.setChecked(False)
        panel_layout.addWidget(self.toggle_active)

        # URL setting for OPEN_URL action
        url_box = QtWidgets.QGroupBox("OPEN_URL target")
        url_layout = QtWidgets.QHBoxLayout(url_box)
        self.url_edit = QtWidgets.QLineEdit("https://www.youtube.com/")
        url_layout.addWidget(self.url_edit)
        panel_layout.addWidget(url_box)

        # Gesture mapping (one dropdown per gesture)
        map_box = QtWidgets.QGroupBox("Gesture → Action bindings")
        map_layout = QtWidgets.QFormLayout(map_box)
        self.combo_map = {}
        for g in GESTURE_LABELS:
            cb = QtWidgets.QComboBox()
            cb.addItems(ACTION_CHOICES)
            # Set default choice if defined
            if g in DEFAULT_BINDINGS:
                idx = cb.findText(DEFAULT_BINDINGS[g])
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            self.combo_map[g] = cb
            map_layout.addRow(g, cb)
        panel_layout.addWidget(map_box)
        panel_layout.addStretch(1)

        # Main layout: left (preview) / right (controls)
        central = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(12)
        h.addWidget(self.video_label, stretch=3)
        h.addWidget(panel, stretch=2)
        self.setCentralWidget(central)

        # ==== Engine ====
        self.engine = GestureEngine(camera_index=0, bindings=self._collect_bindings(), open_url_default=self.url_edit.text())
        self.toggle_active.toggled.connect(self.engine.set_active)
        self.url_edit.editingFinished.connect(self._update_url)
        for g, cb in self.combo_map.items():
            cb.currentTextChanged.connect(self._update_bindings)

        # Timer: fetch frame & render
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000 // 30)  # ~30 FPS
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _collect_bindings(self):
        # Read current bindings from UI
        out = {}
        for g, cb in self.combo_map.items():
            out[g] = cb.currentText()
        return out

    def _update_bindings(self):
        self.engine.set_bindings(self._collect_bindings())

    def _update_url(self):
        self.engine.set_open_url(self.url_edit.text().strip())

    def _on_tick(self):
        frame_bgr, _ = self.engine.step()
        if frame_bgr is None:
            return
        # BGR -> RGB (ensure C-contiguous for QImage)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb = np.ascontiguousarray(frame_rgb)
        h, w, ch = frame_rgb.shape
        qimg = QtGui.QImage(frame_rgb.data, w, h, ch * w, QtGui.QImage.Format.Format_RGB888)
        # Scale to fit the QLabel while keeping aspect ratio
        pix = QtGui.QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(),
            QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pix)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        # Gracefully stop timer and engine when window closes
        try:
            self.timer.stop()
        except Exception:
            pass
        try:
            self.engine.close()
        except Exception:
            pass
        return super().closeEvent(event)

def launch_gui():
    app = QtWidgets.QApplication([])
    mw = MainWindow()
    mw.show()
    app.exec()

if __name__ == "__main__":
    try:
        launch_gui()
    except Exception as e:
        import sys, traceback
        print("App crashed:", e)
        traceback.print_exc()
        sys.exit(1)

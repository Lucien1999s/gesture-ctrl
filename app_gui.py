import numpy as np
import cv2
from PySide6 import QtCore, QtGui, QtWidgets

from src.ui.qt_app import GestureEngine, GESTURE_LABELS, ACTION_CHOICES, DEFAULT_BINDINGS
from src.storage.db import UrlStore

# ---------- URL editor dialogs ----------

class UrlEditDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, name="", url=""):
        super().__init__(parent)
        self.setWindowTitle("Edit URL")
        self.setModal(True)
        form = QtWidgets.QFormLayout(self)
        self.name_edit = QtWidgets.QLineEdit(name)
        self.url_edit  = QtWidgets.QLineEdit(url)
        form.addRow("Name", self.name_edit)
        form.addRow("URL", self.url_edit)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def get_values(self):
        return self.name_edit.text().strip(), self.url_edit.text().strip()

class UrlManagerDialog(QtWidgets.QDialog):
    changed = QtCore.Signal()  # notify parent to refresh combos

    def __init__(self, store: UrlStore, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage URLs")
        self.store = store

        v = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "URL"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        v.addWidget(self.table)

        h = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add")
        self.btn_edit = QtWidgets.QPushButton("Edit")
        self.btn_del = QtWidgets.QPushButton("Delete")
        h.addWidget(self.btn_add); h.addWidget(self.btn_edit); h.addWidget(self.btn_del); h.addStretch(1)
        v.addLayout(h)

        self.btn_add.clicked.connect(self.on_add)
        self.btn_edit.clicked.connect(self.on_edit)
        self.btn_del.clicked.connect(self.on_del)

        self.reload()

    def reload(self):
        rows = self.store.list_urls()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(r["name"]))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(r["url"]))

    def _selected_name(self):
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return None
        return self.table.item(idxs[0].row(), 0).text()

    def on_add(self):
        if self.store.count() >= self.store.LIMIT:
            QtWidgets.QMessageBox.warning(self, "Limit reached", f"Maximum {self.store.LIMIT} URLs.")
            return
        dlg = UrlEditDialog(self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            name, url = dlg.get_values()
            if not name or not url:
                QtWidgets.QMessageBox.warning(self, "Invalid", "Name and URL are required.")
                return
            try:
                self.store.add_url(name, url)
                self.reload()
                self.changed.emit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def on_edit(self):
        name = self._selected_name()
        if not name:
            return
        dlg = UrlEditDialog(self, name, self.store.get_url(name) or "")
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_name, new_url = dlg.get_values()
            if not new_name or not new_url:
                QtWidgets.QMessageBox.warning(self, "Invalid", "Name and URL are required.")
                return
            try:
                self.store.update_url(name, new_name, new_url)
                self.reload()
                self.changed.emit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def on_del(self):
        name = self._selected_name()
        if not name:
            return
        if QtWidgets.QMessageBox.question(self, "Confirm", f"Delete '{name}'?") == QtWidgets.QMessageBox.Yes:
            try:
                self.store.delete_url(name)
                self.reload()
                self.changed.emit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", str(e))

# ---------- Main Window ----------

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("gesture-ctrl")
        self.resize(1150, 700)

        # Left: camera preview
        self.video_label = QtWidgets.QLabel()
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background:#111; border-radius:12px;")

        # Right: settings panel
        panel = QtWidgets.QWidget()
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(10)

        # Toggle
        self.toggle_active = QtWidgets.QCheckBox("Enable gesture control")
        self.toggle_active.setChecked(False)
        panel_layout.addWidget(self.toggle_active)

        # URL manager launcher (no global selection combo)
        self.btn_manage = QtWidgets.QPushButton("Manage URLs…")
        panel_layout.addWidget(self.btn_manage)

        # Gesture → Action bindings (combos will include OPEN_URL:<Name>)
        map_box = QtWidgets.QGroupBox("Gesture → Action bindings")
        map_layout = QtWidgets.QFormLayout(map_box)
        self.combo_map = {}
        panel_layout.addWidget(map_box)
        panel_layout.addStretch(1)

        # Layout composition
        central = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(12)
        h.addWidget(self.video_label, stretch=3)
        h.addWidget(panel, stretch=2)
        self.setCentralWidget(central)

        # Store + Engine
        self.store = UrlStore()
        self.engine = GestureEngine(camera_index=0, bindings=self._default_bindings_resolved(), url_store=self.store)

        # Build gesture combos now that store is ready
        self._build_gesture_combos(map_layout)

        # Wiring
        self.toggle_active.toggled.connect(self.engine.set_active)
        for g, cb in self.combo_map.items():
            cb.currentTextChanged.connect(self._update_bindings)
        self.btn_manage.clicked.connect(self._on_manage_urls)

        # Status bar (show DB path)
        self.statusBar().showMessage(f"DB: {self.store.path}")

        # Timer: fetch frame & render
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000 // 30)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    # ----- Build & refresh choices -----
    def _current_action_choices(self):
        names = self.store.list_names()
        url_actions = [f"OPEN_URL:{n}" for n in names]
        return ACTION_CHOICES + url_actions

    def _build_gesture_combos(self, map_layout: QtWidgets.QFormLayout):
        choices = self._current_action_choices()
        for g in GESTURE_LABELS:
            cb = QtWidgets.QComboBox()
            cb.addItems(choices)
            # set default if provided and present in choices
            if g in DEFAULT_BINDINGS:
                idx = cb.findText(DEFAULT_BINDINGS[g])
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            self.combo_map[g] = cb
            map_layout.addRow(g, cb)

    def _refresh_action_choices_on_all_combos(self):
        choices = self._current_action_choices()
        for g, cb in self.combo_map.items():
            current = cb.currentText()
            cb.blockSignals(True)
            cb.clear()
            cb.addItems(choices)
            if current in choices:
                cb.setCurrentText(current)
            elif g in DEFAULT_BINDINGS and DEFAULT_BINDINGS[g] in choices:
                cb.setCurrentText(DEFAULT_BINDINGS[g])
            else:
                cb.setCurrentIndex(0)
            cb.blockSignals(False)
        self._update_bindings()

    # ----- Bindings helpers -----
    def _default_bindings_resolved(self):
        # DEFAULT_BINDINGS already uses OPEN_URL:<DefaultName>
        return dict(DEFAULT_BINDINGS)

    def _collect_bindings(self):
        return {g: cb.currentText() for g, cb in self.combo_map.items()}

    def _update_bindings(self):
        self.engine.set_bindings(self._collect_bindings())

    # ----- URL manager -----
    def _on_manage_urls(self):
        dlg = UrlManagerDialog(self.store, self)
        dlg.changed.connect(self._refresh_action_choices_on_all_combos)  # live sync while open
        dlg.exec()
        self._refresh_action_choices_on_all_combos()

    # ----- Frame rendering -----
    def _on_tick(self):
        frame_bgr, _ = self.engine.step()
        if frame_bgr is None:
            return
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frame_rgb = np.ascontiguousarray(frame_rgb)
        h, w, ch = frame_rgb.shape
        qimg = QtGui.QImage(frame_rgb.data, w, h, ch * w, QtGui.QImage.Format.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(),
            QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pix)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try: self.timer.stop()
        except Exception: pass
        try: self.engine.close()
        except Exception: pass
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

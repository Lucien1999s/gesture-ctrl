import time
import cv2
from typing import Dict

from PySide6 import QtCore, QtGui, QtWidgets
import mediapipe as mp

from ..paths import MODEL_PATH
from ..logic.geometry import infer_pointing_direction
from ..system.system_controller import SystemController
from ..vision.draw import draw_hands, draw_hud
from ..storage.db import UrlStore  # for default URL name and lookups

# ===== MediaPipe aliases =====
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
GestureRecognizerResult = mp.tasks.vision.GestureRecognizerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# ===== Parameters =====
MIN_SCORE = 0.60
STABLE_FRAMES = 3
COOLDOWN_SEC = 0.5

# Available gestures (with geometric fallback for Pointing_Down)
GESTURE_LABELS = [
    "Thumb_Up",
    "Thumb_Down",
    "Open_Palm",
    "Pointing_Up",
    "Pointing_Down",   # geometric inference
    "Closed_Fist",
    "Victory",
    "ILoveYou",
]

# Base actions (URL options are added in GUI as OPEN_URL:<Name>)
ACTION_CHOICES = [
    "VOL_UP", "VOL_DOWN", "MUTE_TOGGLE",
    "OPEN_CALCULATOR", "OPEN_CLOCK", "OPEN_NOTES", "OPEN_CALENDAR",
    "OPEN_REMINDERS", "OPEN_SAFARI", "OPEN_MAIL", "OPEN_MAPS",
    "OPEN_PHOTOS", "OPEN_MUSIC", "OPEN_LAUNCHPAD",
    "START_SCREENSAVER", "DISPLAY_SLEEP", "WIFI_ON", "WIFI_OFF",
    "BT_ON", "BT_OFF", "DARKMODE_TOGGLE",
    # do NOT include plain "OPEN_URL" here; GUI appends OPEN_URL:<Name>
]

# Default bindings (point ILoveYou to the seeded default URL name)
DEFAULT_BINDINGS = {
    "Thumb_Up":    "VOL_UP",
    "Thumb_Down":  "VOL_DOWN",
    "Open_Palm":   "START_SCREENSAVER",
    "Pointing_Up": "DISPLAY_SLEEP",
    "Closed_Fist": "OPEN_MAPS",
    "Victory":     "OPEN_LAUNCHPAD",
    "ILoveYou":    f"OPEN_URL:{UrlStore.DEFAULT_NAME}",
    # "Pointing_Down": "VOL_DOWN",
}

class GestureEngine(QtCore.QObject):
    """Encapsulates MediaPipe + bindings / debouncing / cooldown + system actions for GUI use."""
    hudChanged = QtCore.Signal(str, str)  # (label, hint)

    def __init__(self, camera_index=0, bindings=None, url_store: UrlStore | None = None):
        super().__init__()
        import os
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        self.camera_index = camera_index
        self.bindings: Dict[str, str] = dict(bindings or DEFAULT_BINDINGS)
        self.active = False  # gesture control toggle (default off)

        self.sys = SystemController()
        self.urls = url_store or UrlStore()   # named URLs (SQLite)

        self.last_result: GestureRecognizerResult | None = None
        self.last_label: str | None = None
        self.overlay_msg, self.overlay_until = None, 0.0

        self.prev_cmd, self.same_count, self.none_count = None, 0, 0
        self.armed, self.last_fire_ts = True, 0.0

        base_options = BaseOptions(model_asset_path=MODEL_PATH)
        options = GestureRecognizerOptions(
            base_options=base_options,
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=self._on_result,
            num_hands=2
        )
        self.recognizer = GestureRecognizer.create_from_options(options)

        # Camera
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_AVFOUNDATION)

        if not self.cap.isOpened():
            self.recognizer.close()
            raise RuntimeError("Cannot open camera")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # FPS
        self.prev_t = time.perf_counter()
        self.fps = 0.0

    # ---- Control interface ----
    def set_active(self, active: bool):
        self.active = active

    def set_bindings(self, bindings: Dict[str, str]):
        self.bindings = dict(bindings)

    # ---- MediaPipe callback ----
    def _on_result(self, result: GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
        self.last_result = result
        label = None
        if result and result.gestures:
            for glist in result.gestures:
                if not glist:
                    continue
                top = glist[0]
                if top.score >= MIN_SCORE:
                    label = f"{top.category_name} {top.score:.2f}"
                    break
        self.last_label = label

    # ---- HUD ----
    def _flash(self, msg, duration=0.7):
        self.overlay_msg, self.overlay_until = msg, time.time() + duration
        self.hudChanged.emit(self.last_label or "", msg)

    # ---- Execute ----
    def _perform(self, cmd: str):
        s = self.sys
        if   cmd == "VOL_UP":               s.volume_up();            self._flash("🔊 Volume +")
        elif cmd == "VOL_DOWN":             s.volume_down();          self._flash("🔉 Volume −")
        elif cmd == "MUTE_TOGGLE":          s.mute_toggle();          self._flash("🔇 Mute")
        elif cmd == "OPEN_CALCULATOR":      s.open_calculator();      self._flash("🧮 Calculator")
        elif cmd == "OPEN_CLOCK":           s.open_clock();           self._flash("⏰ Clock")
        elif cmd == "OPEN_NOTES":           s.open_notes();           self._flash("📝 Notes")
        elif cmd == "OPEN_CALENDAR":        s.open_calendar();        self._flash("📅 Calendar")
        elif cmd == "OPEN_REMINDERS":       s.open_reminders();       self._flash("✅ Reminders")
        elif cmd == "OPEN_SAFARI":          s.open_safari();          self._flash("🧭 Safari")
        elif cmd == "OPEN_MAIL":            s.open_mail();            self._flash("✉️ Mail")
        elif cmd == "OPEN_MAPS":            s.open_maps();            self._flash("🗺 Maps")
        elif cmd == "OPEN_PHOTOS":          s.open_photos();          self._flash("🖼 Photos")
        elif cmd == "OPEN_MUSIC":           s.open_music();           self._flash("🎵 Music")
        elif cmd == "OPEN_LAUNCHPAD":       s.open_launchpad();       self._flash("🟦 Launchpad")
        elif cmd == "START_SCREENSAVER":    s.start_screensaver();    self._flash("🛡 Screensaver")
        elif cmd == "DISPLAY_SLEEP":        s.display_sleep();        self._flash("🌙 Display sleep")
        elif cmd == "WIFI_ON":              s.wifi_on();              self._flash("📶 Wi-Fi ON")
        elif cmd == "WIFI_OFF":             s.wifi_off();             self._flash("📶 Wi-Fi OFF")
        elif cmd == "BT_ON":                s.bt_on();                self._flash("🅱️ Bluetooth ON")
        elif cmd == "BT_OFF":               s.bt_off();               self._flash("🅱️ Bluetooth OFF")
        elif cmd == "DARKMODE_TOGGLE":      s.darkmode_toggle();      self._flash("🌗 Dark Mode")

        elif cmd.startswith("OPEN_URL:"):
            # Per-gesture named URL (e.g., OPEN_URL:YouTube)
            name = cmd.split(":", 1)[1].strip()
            url  = self.urls.get_url(name)
            if url:
                s.open_url(url)
                self._flash(f"🌐 Open URL: {name}")
            else:
                self._flash(f"⚠️ URL preset not found: {name}", 1.2)

        else:
            self._flash(f"(noop) {cmd}", 0.4)

    # ---- Choose command ----
    def _choose_command(self, result: GestureRecognizerResult):
        pd = infer_pointing_direction(result)
        if pd == "Pointing_Down":
            cmd = self.bindings.get("Pointing_Down")
            if cmd:
                return cmd

        if not result or not result.gestures:
            return None
        best_cmd, best_score = None, 0.0
        for glist in result.gestures:
            if not glist:
                continue
            top = glist[0]
            if top.score < MIN_SCORE:
                continue
            label = top.category_name
            cmd = self.bindings.get(label)
            if cmd and top.score > best_score:
                best_cmd, best_score = cmd, top.score
        return best_cmd

    # ---- Step per frame ----
    def step(self):
        ok, frame_bgr = self.cap.read()
        if not ok:
            return None, 0.0

        now = time.perf_counter()
        dt = now - self.prev_t
        self.prev_t = now
        if dt > 0:
            self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt)

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        ts_ms = int(time.perf_counter() * 1000)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        self.recognizer.recognize_async(mp_image, ts_ms)

        if self.active:
            cmd = self._choose_command(self.last_result)
            if cmd is None:
                self.none_count += 1
                if self.none_count >= STABLE_FRAMES:
                    self.armed = True
                self.prev_cmd, self.same_count = None, 0
            else:
                self.none_count = 0
                self.same_count = self.same_count + 1 if cmd == self.prev_cmd else 1
                self.prev_cmd = cmd
                if self.armed and self.same_count >= STABLE_FRAMES and (time.time() - self.last_fire_ts) >= COOLDOWN_SEC:
                    self._perform(cmd)
                    self.last_fire_ts, self.armed = time.time(), False

        if self.last_result:
            draw_hands(frame_bgr, self.last_result)
        hint = self.overlay_msg if time.time() <= self.overlay_until else None
        draw_hud(frame_bgr, self.last_label, self.fps, hint)

        return frame_bgr, self.fps

    def close(self):
        try:
            self.recognizer.close()
        except Exception:
            pass
        try:
            self.urls.close()
        except Exception:
            pass
        try:
            self.cap.release()
        except Exception:
            pass

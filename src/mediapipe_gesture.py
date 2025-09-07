import os
import time
import platform
import subprocess
import threading
import queue
import cv2
import mediapipe as mp

# ===== MediaPipe Tasks =====
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
GestureRecognizerResult = mp.tasks.vision.GestureRecognizerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# ===== UI =====
HAND_CONNECTIONS = mp.solutions.hands.HAND_CONNECTIONS
WINDOW_NAME = "gesture-ctrl (Q / ESC to quit)"
C_LINE = (56, 142, 255)
C_PT = (0, 255, 180)
FONT = cv2.FONT_HERSHEY_SIMPLEX

# ===== Paths =====
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_PATH = os.path.join(_BASE_DIR, "models", "gesture_recognizer.task")

# ===== 基本參數 =====
MIN_SCORE = 0.50
STABLE_FRAMES = 3
COOLDOWN_SEC = 0.5

# ===== macOS actions（全部用系統 API / 指令；不送 keystroke）=====
class MacActions:
    def __init__(self):
        self._vol_step = 6.25  # 每次音量一格左右

    @staticmethod
    def _osascript(script: str) -> bool:
        try:
            subprocess.run(["osascript", "-e", script], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print("[AppleScript ERROR]", e)
            return False

    # --- 音量 ---
    def volume_step(self, delta_percent: float):
        script = f'''
        set ovol to output volume of (get volume settings)
        set nvol to ovol + ({delta_percent})
        if nvol > 100 then set nvol to 100
        if nvol < 0 then set nvol to 0
        set volume output volume nvol'''
        self._osascript(script)

    def volume_up(self):   self.volume_step(+self._vol_step)
    def volume_down(self): self.volume_step(-self._vol_step)

    def mute_toggle(self):
        script = '''
        set omuted to output muted of (get volume settings)
        if omuted then
            set volume without output muted
        else
            set volume with output muted
        end if'''
        self._osascript(script)

    # --- 開 App / 系統功能 ---
    def open_app(self, name: str, alt_paths=()):
        try:
            subprocess.run(["open", "-a", name], check=True)
            return True
        except subprocess.CalledProcessError:
            for p in alt_paths:
                if os.path.exists(p):
                    subprocess.run(["open", p], check=True)
                    return True
        except Exception as e:
            print(f"[Open App] {name} failed:", e)
        return False

    def open_calculator(self): self.open_app("Calculator", ["/System/Applications/Calculator.app"])
    def open_clock(self):
        ok = self.open_app("Clock", ["/System/Applications/Clock.app"])
        if not ok: print("[Clock] app not found on this macOS.")
    def open_notes(self):      self.open_app("Notes", ["/System/Applications/Notes.app"])
    def open_calendar(self):   self.open_app("Calendar", ["/System/Applications/Calendar.app"])
    def open_reminders(self):  self.open_app("Reminders", ["/System/Applications/Reminders.app"])
    def open_safari(self):     self.open_app("Safari", ["/System/Applications/Safari.app"])
    def open_mail(self):       self.open_app("Mail", ["/System/Applications/Mail.app"])
    def open_maps(self):       self.open_app("Maps", ["/System/Applications/Maps.app"])
    def open_photos(self):     self.open_app("Photos", ["/System/Applications/Photos.app"])
    def open_music(self):      self.open_app("Music", ["/System/Applications/Music.app"])
    def open_launchpad(self):
        try: subprocess.run(["open", "-a", "Launchpad"], check=True)
        except Exception as e: print("[Launchpad] open failed:", e)

    def start_screensaver(self):
        try: subprocess.run(["open", "-a", "ScreenSaverEngine"], check=True)
        except Exception as e: print("[Screensaver] start failed:", e)

    def display_sleep(self):
        try: subprocess.run(["pmset", "displaysleepnow"], check=True)
        except Exception as e: print("[DisplaySleep] failed:", e)

    # Wi-Fi 需要正確的服務名稱，預設 "Wi-Fi"
    def wifi_on(self, service="Wi-Fi"):
        try: subprocess.run(["networksetup", "-setairportpower", service, "on"], check=True)
        except Exception as e: print("[Wi-Fi ON] failed:", e)
    def wifi_off(self, service="Wi-Fi"):
        try: subprocess.run(["networksetup", "-setairportpower", service, "off"], check=True)
        except Exception as e: print("[Wi-Fi OFF] failed:", e)

    # 藍牙需安裝 blueutil: brew install blueutil
    def bt_on(self):
        try: subprocess.run(["blueutil", "--power", "1"], check=True)
        except Exception as e: print("[Bluetooth ON] failed (need blueutil?):", e)
    def bt_off(self):
        try: subprocess.run(["blueutil", "--power", "0"], check=True)
        except Exception as e: print("[Bluetooth OFF] failed (need blueutil?):", e)

    def darkmode_toggle(self):
        script = '''
        tell application "System Events"
            tell appearance preferences
                set dark mode to not dark mode
            end tell
        end tell'''
        self._osascript(script)

    def open_url(self, url: str):
        try: subprocess.run(["open", url], check=True)
        except Exception as e: print("[Open URL] failed:", e)

class SystemController:
    def __init__(self):
        self.os = platform.system().lower()
        self.mac = MacActions() if ("darwin" in self.os or "mac" in self.os) else None

    # 音量
    def volume_up(self):          self.mac.volume_up()          if self.mac else print("[Volume] up stub")
    def volume_down(self):        self.mac.volume_down()        if self.mac else print("[Volume] down stub")
    def mute_toggle(self):        self.mac.mute_toggle()        if self.mac else print("[Mute] stub")

    # 開 App
    def open_calculator(self):    self.mac.open_calculator()    if self.mac else print("[Calculator] stub")
    def open_clock(self):         self.mac.open_clock()         if self.mac else print("[Clock] stub")
    def open_notes(self):         self.mac.open_notes()         if self.mac else print("[Notes] stub")
    def open_calendar(self):      self.mac.open_calendar()      if self.mac else print("[Calendar] stub")
    def open_reminders(self):     self.mac.open_reminders()     if self.mac else print("[Reminders] stub")
    def open_safari(self):        self.mac.open_safari()        if self.mac else print("[Safari] stub")
    def open_mail(self):          self.mac.open_mail()          if self.mac else print("[Mail] stub")
    def open_maps(self):          self.mac.open_maps()          if self.mac else print("[Maps] stub")
    def open_photos(self):        self.mac.open_photos()        if self.mac else print("[Photos] stub")
    def open_music(self):         self.mac.open_music()         if self.mac else print("[Music] stub")
    def open_launchpad(self):     self.mac.open_launchpad()     if self.mac else print("[Launchpad] stub")

    # 系統
    def start_screensaver(self):  self.mac.start_screensaver()  if self.mac else print("[Screensaver] stub")
    def display_sleep(self):      self.mac.display_sleep()      if self.mac else print("[DisplaySleep] stub")
    def wifi_on(self):            self.mac.wifi_on()            if self.mac else print("[Wi-Fi ON] stub")
    def wifi_off(self):           self.mac.wifi_off()           if self.mac else print("[Wi-Fi OFF] stub")
    def bt_on(self):              self.mac.bt_on()              if self.mac else print("[BT ON] stub")
    def bt_off(self):             self.mac.bt_off()             if self.mac else print("[BT OFF] stub")
    def darkmode_toggle(self):    self.mac.darkmode_toggle()    if self.mac else print("[DarkMode] stub")
    def open_url(self, url):      self.mac.open_url(url)        if self.mac else print(f"[Open URL] {url}")

# ===== 視覺化 =====
def _draw_hands(frame_bgr, result: GestureRecognizerResult):
    if not result or not result.hand_landmarks: return
    h, w = frame_bgr.shape[:2]
    for landmarks in result.hand_landmarks:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for a, b in HAND_CONNECTIONS:
            if 0 <= a < len(pts) and 0 <= b < len(pts):
                cv2.line(frame_bgr, pts[a], pts[b], C_LINE, 2, cv2.LINE_AA)
        for (x, y) in pts:
            cv2.circle(frame_bgr, (x, y), 3, C_PT, -1, cv2.LINE_AA)

def _draw_hud(frame_bgr, label, fps, hint=None):
    if label:
        (tw, th), _ = cv2.getTextSize(label, FONT, 0.8, 2)
        pad = 8; x, y = 12, 40
        cv2.rectangle(frame_bgr, (x - pad, y - th - pad), (x + tw + pad, y + pad), (0, 0, 0), -1)
        cv2.putText(frame_bgr, label, (x, y), FONT, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame_bgr, f"{fps:.1f} FPS", (12, 70), FONT, 0.6, (200, 255, 200), 2, cv2.LINE_AA)
    if hint:
        cv2.putText(frame_bgr, hint, (12, 100), FONT, 0.7, (0, 220, 255), 2, cv2.LINE_AA)

# ===== App（背景執行緒避免卡畫面）=====
class MediaPipeGestureApp:
    """
    bindings: dict[str, str]
      例：{"Thumb_Up":"VOL_UP", "Victory":"OPEN_CALCULATOR", ...}
    opts: dict，可帶參數：
      - "open_url_default": 預設網址（給 OPEN_URL 用）
    """
    def __init__(self, camera_index=0, bindings=None, opts=None):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        self.camera_index = camera_index
        self.bindings = bindings or {}
        self.opts = opts or {}
        self.url_default = self.opts.get("open_url_default", "https://www.google.com")

        self.last_result, self.last_label = None, None
        self.prev_cmd, self.same_count, self.none_count = None, 0, 0
        self.armed, self.last_fire_ts = True, 0.0
        self.overlay_msg, self.overlay_until = None, 0.0

        self.sys = SystemController()

        # 動作隊列與執行緒
        self.cmd_q: "queue.Queue[str]" = queue.Queue()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

        base_options = BaseOptions(model_asset_path=MODEL_PATH)
        options = GestureRecognizerOptions(
            base_options=base_options,
            running_mode=VisionRunningMode.LIVE_STREAM,
            result_callback=self._on_result,
            num_hands=2
        )
        self.recognizer = GestureRecognizer.create_from_options(options)

    def _worker(self):
        while True:
            cmd = self.cmd_q.get()
            try:
                self._perform(cmd)
            except Exception as e:
                print("[perform ERROR]", e)
            finally:
                self.cmd_q.task_done()

    # ---- MediaPipe callback ----
    def _on_result(self, result: GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
        self.last_result = result
        label = None
        if result and result.gestures:
            for glist in result.gestures:
                if not glist: continue
                top = glist[0]
                if top.score >= MIN_SCORE:
                    label = f"{top.category_name} {top.score:.2f}"
                    break
        self.last_label = label

    # ---- 選擇命令 ----
    def _choose_command(self, result: GestureRecognizerResult):
        if not result or not result.gestures:
            return None
        best_cmd, best_score = None, 0.0
        for glist in result.gestures:
            if not glist: continue
            top = glist[0]
            if top.score < MIN_SCORE: continue
            label = top.category_name
            cmd = self.bindings.get(label)
            if cmd and top.score > best_score:
                best_cmd, best_score = cmd, top.score
        return best_cmd

    # ---- 顯示 HUD ----
    def _flash(self, msg, duration=0.7):
        self.overlay_msg, self.overlay_until = msg, time.time() + duration

    # ---- 執行命令（在背景執行緒）----
    def _perform(self, cmd: str):
        # 音量
        if   cmd == "VOL_UP":               self.sys.volume_up();            self._flash("🔊 Volume +")
        elif cmd == "VOL_DOWN":             self.sys.volume_down();          self._flash("🔉 Volume −")
        elif cmd == "MUTE_TOGGLE":          self.sys.mute_toggle();          self._flash("🔇 Mute")

        # 開 App
        elif cmd == "OPEN_CALCULATOR":      self.sys.open_calculator();      self._flash("🧮 Calculator")
        elif cmd == "OPEN_CLOCK":           self.sys.open_clock();           self._flash("⏰ Clock")
        elif cmd == "OPEN_NOTES":           self.sys.open_notes();           self._flash("📝 Notes")
        elif cmd == "OPEN_CALENDAR":        self.sys.open_calendar();        self._flash("📅 Calendar")
        elif cmd == "OPEN_REMINDERS":       self.sys.open_reminders();       self._flash("✅ Reminders")
        elif cmd == "OPEN_SAFARI":          self.sys.open_safari();          self._flash("🧭 Safari")
        elif cmd == "OPEN_MAIL":            self.sys.open_mail();            self._flash("✉️ Mail")
        elif cmd == "OPEN_MAPS":            self.sys.open_maps();            self._flash("🗺 Maps")
        elif cmd == "OPEN_PHOTOS":          self.sys.open_photos();          self._flash("🖼 Photos")
        elif cmd == "OPEN_MUSIC":           self.sys.open_music();           self._flash("🎵 Music")
        elif cmd == "OPEN_LAUNCHPAD":       self.sys.open_launchpad();       self._flash("🟦 Launchpad")

        # 系統
        elif cmd == "START_SCREENSAVER":    self.sys.start_screensaver();    self._flash("🛡 Screensaver")
        elif cmd == "DISPLAY_SLEEP":        self.sys.display_sleep();        self._flash("🌙 Display sleep")
        elif cmd == "WIFI_ON":              self.sys.wifi_on();              self._flash("📶 Wi-Fi ON")
        elif cmd == "WIFI_OFF":             self.sys.wifi_off();             self._flash("📶 Wi-Fi OFF")
        elif cmd == "BT_ON":                self.sys.bt_on();                self._flash("🅱️ Bluetooth ON")
        elif cmd == "BT_OFF":               self.sys.bt_off();               self._flash("🅱️ Bluetooth OFF")
        elif cmd == "DARKMODE_TOGGLE":      self.sys.darkmode_toggle();      self._flash("🌗 Dark Mode")

        # 網址
        elif cmd == "OPEN_URL":             self.sys.open_url(self.url_default); self._flash("🌐 Open URL")

        else:
            self._flash(f"(noop) {cmd}", 0.4)

    # ---- 節流與觸發 ----
    def _maybe_fire(self):
        cmd = self._choose_command(self.last_result)
        if cmd is None:
            self.none_count += 1
            if self.none_count >= STABLE_FRAMES: self.armed = True
            self.prev_cmd, self.same_count = None, 0
            return
        self.none_count = 0
        self.same_count = self.same_count + 1 if cmd == self.prev_cmd else 1
        self.prev_cmd = cmd
        if not self.armed: return
        if self.same_count >= STABLE_FRAMES and (time.time() - self.last_fire_ts) >= COOLDOWN_SEC:
            self.cmd_q.put(cmd)
            self.last_fire_ts, self.armed = time.time(), False

    # ---- 主迴圈 ----
    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.recognizer.close()
            raise RuntimeError("無法開啟攝影機")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        prev_time, fps = time.perf_counter(), 0.0
        try:
            while True:
                ok, frame_bgr = cap.read()
                if not ok: continue
                now = time.perf_counter(); dt = now - prev_time; prev_time = now
                if dt > 0: fps = 0.9 * fps + 0.1 * (1.0 / dt)

                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                ts_ms = int(time.perf_counter() * 1000)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                self.recognizer.recognize_async(mp_image, ts_ms)

                self._maybe_fire()

                if self.last_result: _draw_hands(frame_bgr, self.last_result)
                hint = self.overlay_msg if time.time() <= self.overlay_until else None
                _draw_hud(frame_bgr, self.last_label, fps, hint)

                cv2.imshow(WINDOW_NAME, frame_bgr)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), ord('Q'), 27): break
                if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1: break
        finally:
            try: self.recognizer.close()
            except Exception: pass
            cap.release()
            cv2.destroyAllWindows()
            cv2.waitKey(1)
            time.sleep(0.05)

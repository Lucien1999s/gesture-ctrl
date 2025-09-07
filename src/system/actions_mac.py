import os
import subprocess

class MacActions:
    def __init__(self, vol_step=6.25):
        self._vol_step = vol_step  # each ≈ 6.25%

    @staticmethod
    def _osascript(script: str) -> bool:
        try:
            subprocess.run(["osascript", "-e", script], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print("[AppleScript ERROR]", e)
            return False

    # Volume
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

    # Open App / system functions
    def _open_app(self, name: str, alt_paths=()):
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

    def open_calculator(self): self._open_app("Calculator", ["/System/Applications/Calculator.app"])
    def open_clock(self):      self._open_app("Clock", ["/System/Applications/Clock.app"])
    def open_notes(self):      self._open_app("Notes", ["/System/Applications/Notes.app"])
    def open_calendar(self):   self._open_app("Calendar", ["/System/Applications/Calendar.app"])
    def open_reminders(self):  self._open_app("Reminders", ["/System/Applications/Reminders.app"])
    def open_safari(self):     self._open_app("Safari", ["/System/Applications/Safari.app"])
    def open_mail(self):       self._open_app("Mail", ["/System/Applications/Mail.app"])
    def open_maps(self):       self._open_app("Maps", ["/System/Applications/Maps.app"])
    def open_photos(self):     self._open_app("Photos", ["/System/Applications/Photos.app"])
    def open_music(self):      self._open_app("Music", ["/System/Applications/Music.app"])
    def open_launchpad(self):
        try: subprocess.run(["open", "-a", "Launchpad"], check=True)
        except Exception as e: print("[Launchpad] open failed:", e)

    def start_screensaver(self):
        try: subprocess.run(["open", "-a", "ScreenSaverEngine"], check=True)
        except Exception as e: print("[Screensaver] start failed:", e)

    def display_sleep(self):
        try: subprocess.run(["pmset", "displaysleepnow"], check=True)
        except Exception as e: print("[DisplaySleep] failed:", e)

    def wifi_on(self, service="Wi-Fi"):
        try: subprocess.run(["networksetup", "-setairportpower", service, "on"], check=True)
        except Exception as e: print("[Wi-Fi ON] failed:", e)

    def wifi_off(self, service="Wi-Fi"):
        try: subprocess.run(["networksetup", "-setairportpower", service, "off"], check=True)
        except Exception as e: print("[Wi-Fi OFF] failed:", e)

    # Need `brew install blueutil`
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

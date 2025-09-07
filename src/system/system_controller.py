import platform
from .actions_mac import MacActions

class SystemController:
    def __init__(self):
        osname = platform.system().lower()
        self._mac = MacActions() if ("darwin" in osname or "mac" in osname) else None

    # Volume
    def volume_up(self):     self._mac.volume_up()     if self._mac else print("[Volume] up stub")
    def volume_down(self):   self._mac.volume_down()   if self._mac else print("[Volume] down stub")
    def mute_toggle(self):   self._mac.mute_toggle()   if self._mac else print("[Mute] stub")

    # Open App
    def open_calculator(self): self._mac.open_calculator() if self._mac else print("[Calculator] stub")
    def open_clock(self):      self._mac.open_clock()      if self._mac else print("[Clock] stub")
    def open_notes(self):      self._mac.open_notes()      if self._mac else print("[Notes] stub")
    def open_calendar(self):   self._mac.open_calendar()   if self._mac else print("[Calendar] stub")
    def open_reminders(self):  self._mac.open_reminders()  if self._mac else print("[Reminders] stub")
    def open_safari(self):     self._mac.open_safari()     if self._mac else print("[Safari] stub")
    def open_mail(self):       self._mac.open_mail()       if self._mac else print("[Mail] stub")
    def open_maps(self):       self._mac.open_maps()       if self._mac else print("[Maps] stub")
    def open_photos(self):     self._mac.open_photos()     if self._mac else print("[Photos] stub")
    def open_music(self):      self._mac.open_music()      if self._mac else print("[Music] stub")
    def open_launchpad(self):  self._mac.open_launchpad()  if self._mac else print("[Launchpad] stub")

    # System
    def start_screensaver(self): self._mac.start_screensaver() if self._mac else print("[Screensaver] stub")
    def display_sleep(self):     self._mac.display_sleep()     if self._mac else print("[DisplaySleep] stub")
    def wifi_on(self):           self._mac.wifi_on()           if self._mac else print("[Wi-Fi ON] stub")
    def wifi_off(self):          self._mac.wifi_off()          if self._mac else print("[Wi-Fi OFF] stub")
    def bt_on(self):             self._mac.bt_on()             if self._mac else print("[BT ON] stub")
    def bt_off(self):            self._mac.bt_off()            if self._mac else print("[BT OFF] stub")
    def darkmode_toggle(self):   self._mac.darkmode_toggle()   if self._mac else print("[DarkMode] stub")

    # Web Url
    def open_url(self, url: str): self._mac.open_url(url) if self._mac else print(f"[Open URL] {url}")

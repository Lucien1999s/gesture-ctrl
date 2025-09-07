from src.mediapipe_gesture import MediaPipeGestureApp

"""
你可以在這裡自由設定「七個手勢」要做什麼。
可用的手勢標籤：
  Thumb_Up, Thumb_Down, Open_Palm, Pointing_Up, Closed_Fist, Victory, ILoveYou

可用的動作字串（任選其一綁到手勢）：

# 音量
  "VOL_UP" , "VOL_DOWN" , "MUTE_TOGGLE"

# 開啟內建 App
  "OPEN_CALCULATOR", "OPEN_CLOCK", "OPEN_NOTES", "OPEN_CALENDAR",
  "OPEN_REMINDERS", "OPEN_SAFARI", "OPEN_MAIL", "OPEN_MAPS",
  "OPEN_PHOTOS", "OPEN_MUSIC", "OPEN_LAUNCHPAD"

# 系統功能
  "START_SCREENSAVER", "DISPLAY_SLEEP", "WIFI_ON", "WIFI_OFF",
  "BT_ON", "BT_OFF", "DARKMODE_TOGGLE"

# 網址
  "OPEN_URL"   ← 將開啟 opts["open_url_default"] 指定的網址（預設 Google）
"""

# 這裡改就能重新綁定
GESTURE_BINDINGS = {
    "Thumb_Up":    "VOL_UP",
    "Thumb_Down":  "VOL_DOWN",
    "Open_Palm":   "START_SCREENSAVER",
    "Pointing_Up": "DISPLAY_SLEEP",
    "Closed_Fist": "OPEN_MAPS",
    "Victory":     "OPEN_LAUNCHPAD",
    "ILoveYou":    "OPEN_URL",
}

# 可選：設定 OPEN_URL 的預設網址（你也可改成公司首頁、Google 搜尋等）
OPTS = {
    "open_url_default": "https://www.youtube.com/",
}

def main():
    app = MediaPipeGestureApp(camera_index=0, bindings=GESTURE_BINDINGS, opts=OPTS)
    app.run()

if __name__ == "__main__":
    main()

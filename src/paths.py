import os
import sys

def _base_dir():
    # Support PyInstaller (_MEIPASS)
    if hasattr(sys, "_MEIPASS") and sys._MEIPASS:
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def resource_path(*relative):
    return os.path.join(_base_dir(), *relative)

BASE_DIR = _base_dir()
MODEL_PATH = resource_path("models", "gesture_recognizer.task")

# UI Colors
WINDOW_NAME = "gesture-ctrl (Q / ESC to quit)"
C_LINE = (56, 142, 255)
C_PT = (0, 255, 180)

import os
import sys

def _base_dir() -> str:
    """
    Return the base directory of the project.

    - When running as a PyInstaller bundle, sys._MEIPASS points to the temp dir.
    - Otherwise, fallback to project root (parent of this file).
    """
    if hasattr(sys, "_MEIPASS"):  # PyInstaller adds this attribute
        return sys._MEIPASS
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def resource_path(*relative: str) -> str:
    """
    Join one or more relative path components onto the base directory.
    """
    return os.path.join(_base_dir(), *relative)

# === Paths ===
BASE_DIR   = _base_dir()
MODEL_PATH = resource_path("models", "gesture_recognizer.task")

# === UI constants ===
WINDOW_NAME = "gesture-ctrl (Q / ESC to quit)"
C_LINE = (56, 142, 255)   # Line color for hand skeleton
C_PT   = (0, 255, 180)    # Point color for landmarks

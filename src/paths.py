import os

# Repo base direction
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Mode file location
MODEL_PATH = os.path.join(BASE_DIR, "models", "gesture_recognizer.task")

# Windows/Parameters
WINDOW_NAME = "gesture-ctrl (Q / ESC to quit)"
C_LINE = (56, 142, 255)
C_PT = (0, 255, 180)

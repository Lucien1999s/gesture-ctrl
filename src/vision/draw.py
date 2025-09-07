import time
import cv2
from mediapipe import solutions as mp_solutions
from ..paths import C_LINE, C_PT

HAND_CONNECTIONS = mp_solutions.hands.HAND_CONNECTIONS
FONT = cv2.FONT_HERSHEY_SIMPLEX

def draw_hands(frame_bgr, result):
    if not result or not result.hand_landmarks:
        return
    h, w = frame_bgr.shape[:2]
    for landmarks in result.hand_landmarks:
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for a, b in HAND_CONNECTIONS:
            if 0 <= a < len(pts) and 0 <= b < len(pts):
                cv2.line(frame_bgr, pts[a], pts[b], C_LINE, 2, cv2.LINE_AA)
        for (x, y) in pts:
            cv2.circle(frame_bgr, (x, y), 3, C_PT, -1, cv2.LINE_AA)

def draw_hud(frame_bgr, label: str | None, fps: float, hint: str | None = None):
    if label:
        (tw, th), _ = cv2.getTextSize(label, FONT, 0.8, 2)
        pad = 8; x, y = 12, 40
        cv2.rectangle(frame_bgr, (x - pad, y - th - pad), (x + tw + pad, y + pad), (0, 0, 0), -1)
        cv2.putText(frame_bgr, label, (x, y), FONT, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame_bgr, f"{fps:.1f} FPS", (12, 70), FONT, 0.6, (200, 255, 200), 2, cv2.LINE_AA)
    if hint:
        cv2.putText(frame_bgr, hint, (12, 100), FONT, 0.7, (0, 220, 255), 2, cv2.LINE_AA)

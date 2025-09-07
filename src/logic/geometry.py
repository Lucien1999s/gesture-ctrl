import math
from mediapipe import solutions as mp_solutions
from mediapipe.tasks.python.vision import GestureRecognizerResult

HAND_CONNECTIONS = mp_solutions.hands.HAND_CONNECTIONS

# Geometric redundancy parameters
ORIENT_THRESH = 0.05       # Y-axis threshold (image coordinate y is positive downwards)
STRAIGHT_COS = -0.85       # An angle close to 180° is considered straight

def _cos_between(ax, ay, bx, by):
    na = math.hypot(ax, ay)
    nb = math.hypot(bx, by)
    if na == 0 or nb == 0:
        return 1.0
    return (ax*bx + ay*by) / (na*nb)

def index_is_straight(lm):
    # Determine by PIP angle (MCP->PIP and PIP->DIP)
    mcp = lm[5]; pip = lm[6]; dip = lm[7]
    v1x, v1y = (pip.x - mcp.x), (pip.y - mcp.y)
    v2x, v2y = (dip.x - pip.x), (dip.y - pip.y)
    cospip = _cos_between(v1x, v1y, v2x, v2y)
    return cospip <= STRAIGHT_COS

def infer_pointing_direction(result: GestureRecognizerResult) -> str | None:
    """
    Returns "Pointing_Up" / "Pointing_Down" / None
    Performs fallback inference when the model doesn't have a Pointing_Down state.
    """
    if not result or not result.hand_landmarks:
        return None
    for lm in result.hand_landmarks:
        if len(lm) < 21:
            continue
        if not index_is_straight(lm):
            continue
        tip = lm[8]; mcp = lm[5]
        dy = tip.y - mcp.y
        if dy < -ORIENT_THRESH:
            return "Pointing_Up"
        if dy > ORIENT_THRESH:
            return "Pointing_Down"
    return None

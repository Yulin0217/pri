"""Screen-capture helpers shared across the client and data-collection scripts.

The pCLE live view is read directly from the screen with `mss`. The capture
rectangle is hard-coded for one monitor layout; use `tools/test.py` to find the
correct coordinates for your setup and update PCLE_VIEW below.
"""

import cv2
import numpy as np
from mss import mss

# Screen rectangle of the pCLE live view, in pixels. Update for your layout.
PCLE_VIEW = {"top": 45, "left": 1118, "width": 350, "height": 350}


def capture_partial_screen(top, left, width, height, gray=True):
    """Grab a screen rectangle and return it as an OpenCV image.

    gray=True returns a single-channel grayscale image, otherwise BGR.
    """
    with mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}
        frame = np.array(sct.grab(monitor))
    if gray:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def capture_pcle_view(gray=True):
    """Capture the pCLE live-view region defined by PCLE_VIEW."""
    return capture_partial_screen(
        PCLE_VIEW["top"], PCLE_VIEW["left"],
        PCLE_VIEW["width"], PCLE_VIEW["height"], gray=gray,
    )

"""Screen capture using the active machine configuration."""

import cv2
import numpy as np
from mss import mss
from .config import get_settings


def capture_partial_screen(top, left, width, height, gray=True):
    """Capture a desktop rectangle in pixels as grayscale or OpenCV BGR data."""
    # Construct the capture context in its calling thread, including the sender.
    with mss() as screen:
        frame = np.asarray(screen.grab(dict(top=top, left=left, width=width, height=height)))
    # mss supplies BGRA pixels; remove alpha and use the correct channel order.
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY if gray else cv2.COLOR_BGRA2BGR)


def capture_pcle_view(gray=True):
    """Read the live probe-image region from this computer's display layout."""
    return capture_partial_screen(**get_settings().capture.pcle_view, gray=gray)


def capture_mosaic_view(gray=True):
    """Read the viewer's mosaic region, distinct from the raw probe frame."""
    return capture_partial_screen(**get_settings().capture.mosaic_view, gray=gray)

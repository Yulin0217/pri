"""Core mosaicking primitives shared by the direct and regression scripts.

A pCLE probe has a small field of view. To image a larger area the probe is
scanned over the sample and the individual frames are stitched into one large
image (a mosaic). `MosaicCanvas` places each frame onto a big canvas, either by
a physical stage position (metres) or by a pixel offset (e.g. from a regression
model), and blends overlapping frames.
"""

import cv2
import numpy as np


def build_spiral_trajectory(spiral_wind=1.12, r_scale=1e-4,
                            coarse_stop=5.0, coarse_step=0.3,
                            fine_stop=8.0, fine_step=0.08):
    """Return a list of (x_m, y_m) stage positions along an Archimedean-like
    spiral, matching the scan used by apps/demo.py.

    spiral_wind > 1 tightens the rings; a smaller step samples more densely.
    r_scale converts the dimensionless radius to metres.
    """
    steps = np.concatenate((
        np.arange(0.0, coarse_stop, coarse_step),
        np.arange(coarse_stop, fine_stop, fine_step),
    ))
    trajectory = []
    for i in steps:
        ang = i * np.pi * spiral_wind
        x = i * np.cos(ang) * r_scale
        y = i * np.sin(ang) * r_scale
        trajectory.append((float(x), float(y)))
    return trajectory


def estimate_canvas_size(trajectory, meters_per_pixel, frame_shape, margin_px=50):
    """Return (height_px, width_px) large enough to hold every frame placed
    along `trajectory`, plus a margin."""
    xs = [p[0] for p in trajectory]
    ys = [p[1] for p in trajectory]
    span_x_px = (max(xs) - min(xs)) / meters_per_pixel
    span_y_px = (max(ys) - min(ys)) / meters_per_pixel
    fh, fw = frame_shape[:2]
    width = int(round(span_x_px + fw + 2 * margin_px))
    height = int(round(span_y_px + fh + 2 * margin_px))
    return height, width


class MosaicCanvas:
    """Accumulates frames into a single grayscale mosaic image.

    Parameters
    ----------
    height_px, width_px : int
        Canvas size in pixels.
    meters_per_pixel : float
        Stage travel (metres) per mosaic pixel. Calibrate for your optics;
        only used by place_meters().
    blend : {"average", "max", "overwrite"}
        How overlapping frames combine. "average" is smooth, "max" keeps the
        brightest signal (useful for fluorescence), "overwrite" keeps the last.
    sign_x, sign_y : int
        +1 / -1 to align stage axes with image axes; calibrate per setup.
    """

    def __init__(self, height_px, width_px, meters_per_pixel,
                 blend="average", sign_x=1, sign_y=1):
        self.h = int(height_px)
        self.w = int(width_px)
        self.mpp = float(meters_per_pixel)
        self.blend = blend
        self.sign_x = sign_x
        self.sign_y = sign_y
        self.cx = self.w // 2
        self.cy = self.h // 2
        self.accum = np.zeros((self.h, self.w), np.float32)
        self.weight = np.zeros((self.h, self.w), np.float32)
        self.canvas = np.zeros((self.h, self.w), np.float32)

    def place_center_px(self, image, dx_px, dy_px):
        """Place `image` centred at (canvas_center + dx_px, canvas_center + dy_px).

        Returns True if any part of the frame landed on the canvas.
        """
        img = np.asarray(image)
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ih, iw = img.shape[:2]

        fx = self.cx + dx_px
        fy = self.cy + dy_px
        x0 = int(round(fx - iw / 2.0))
        y0 = int(round(fy - ih / 2.0))

        # Intersect the frame rectangle with the canvas.
        x0c, y0c = max(x0, 0), max(y0, 0)
        x1c, y1c = min(x0 + iw, self.w), min(y0 + ih, self.h)
        if x1c <= x0c or y1c <= y0c:
            return False

        patch = img[y0c - y0:y1c - y0, x0c - x0:x1c - x0].astype(np.float32)
        if self.blend == "average":
            self.accum[y0c:y1c, x0c:x1c] += patch
            self.weight[y0c:y1c, x0c:x1c] += 1.0
        elif self.blend == "max":
            region = self.canvas[y0c:y1c, x0c:x1c]
            self.canvas[y0c:y1c, x0c:x1c] = np.maximum(region, patch)
        else:  # overwrite
            self.canvas[y0c:y1c, x0c:x1c] = patch
        return True

    def place_meters(self, image, x_m, y_m):
        """Place `image` centred at stage position (x_m, y_m)."""
        dx_px = self.sign_x * x_m / self.mpp
        dy_px = -self.sign_y * y_m / self.mpp  # image Y points down
        return self.place_center_px(image, dx_px, dy_px)

    def render(self):
        """Return the current mosaic as a uint8 grayscale image."""
        if self.blend == "average":
            out = np.zeros((self.h, self.w), np.float32)
            mask = self.weight > 0
            out[mask] = self.accum[mask] / self.weight[mask]
            return np.clip(out, 0, 255).astype(np.uint8)
        return np.clip(self.canvas, 0, 255).astype(np.uint8)

    def save(self, path):
        """Render and write the mosaic to `path`."""
        cv2.imwrite(path, self.render())

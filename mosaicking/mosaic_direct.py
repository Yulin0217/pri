"""Direct mosaicking (local, no network).

Scans the probe over a local spiral trajectory and places every captured pCLE
frame onto the mosaic canvas using the SmarPod's commanded (x, y) pose. The
mosaic geometry therefore comes entirely from the stage positions and the
calibrated pixel scale.

Run:
    python mosaicking/mosaic_direct.py
"""

import json
import os
import sys
import time
from pathlib import Path

import cv2

# Make the repo root importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import smaract.smarpod as smarpod
from smaract.smarpod import Pose

from common.capture import capture_pcle_view
from common.utils_client import SmarPod_init, pose_to_str
from mosaicking.mosaic_core import (
    build_spiral_trajectory, estimate_canvas_size, MosaicCanvas,
)

# ---- Configuration --------------------------------------------------------
METERS_PER_PIXEL = 1e-6   # CALIBRATE: stage travel per mosaic pixel (m/px)
BLEND = "average"         # "average" | "max" | "overwrite"
SIGN_X = 1                # flip to align stage X with image X (+1 / -1)
SIGN_Y = 1                # flip to align stage Y with image Y (+1 / -1)
SETTLE_S = 0.6            # settle time after each move, before capturing
SPEED_M_S = 2e-3          # between 1e-3 (slow) and init default 3e-3
SAVE_EVERY = 20           # write the current mosaic every N frames (0 disables)
# ---------------------------------------------------------------------------


def safe_shutdown(h):
    if h is None:
        return
    try:
        smarpod.Move(h, Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0, True)
        smarpod.Stop(h)
    finally:
        smarpod.Close(h)
        print("device closed")


def main():
    out_dir = time.strftime("mosaic_direct_%Y-%m-%d_%H-%M-%S")
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    mosaic_path = os.path.join(out_dir, "mosaic.png")

    # Smaller coarse_step: inner rings closer (reduces seam at the old coarse/fine join).
    trajectory = build_spiral_trajectory(coarse_step=0.2, fine_step=0.065)
    print("trajectory length:", len(trajectory))

    h = None
    canvas = None
    poses = {}
    try:
        h = SmarPod_init()
        smarpod.SetSpeed(h, 1, SPEED_M_S)
        print("stage speed: %.3e m/s (%.2f mm/s)" % (SPEED_M_S, SPEED_M_S * 1e3))
        csys = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        smarpod.SetCoordinateSystem(h, csys)
        smarpod.Move(h, Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0, True)
        time.sleep(SETTLE_S)

        sample = capture_pcle_view(gray=True)
        height, width = estimate_canvas_size(trajectory, METERS_PER_PIXEL, sample.shape)
        canvas = MosaicCanvas(height, width, METERS_PER_PIXEL, BLEND, SIGN_X, SIGN_Y)
        print("mosaic canvas size: %dx%d px (frame %dx%d)" % (width, height, sample.shape[1], sample.shape[0]))

        for idx, (x, y) in enumerate(trajectory):
            pose = Pose(x, y, 0.0, 0.0, 0.0, 0.0)
            if not smarpod.IsPoseReachable(h, pose):
                print("skip unreachable pose %d: %s" % (idx, pose_to_str(pose)))
                continue

            smarpod.Move(h, pose, 0, True)
            time.sleep(SETTLE_S)

            frame = capture_pcle_view(gray=True)
            canvas.place_meters(frame, x, y)
            cv2.imwrite(os.path.join(frames_dir, "frame_%04d.png" % idx), frame)
            poses[idx] = {"x_m": x, "y_m": y, "pose": pose_to_str(pose)}
            print("placed frame %04d at x=%+.4e y=%+.4e" % (idx, x, y))

            if SAVE_EVERY and (idx + 1) % SAVE_EVERY == 0:
                canvas.save(mosaic_path)

        smarpod.Move(h, Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0, True)
    except KeyboardInterrupt:
        print("\nInterrupted by user; saving mosaic so far.")
    finally:
        if canvas is not None:
            canvas.save(mosaic_path)
            print("mosaic saved to %s" % mosaic_path)
        with open(os.path.join(out_dir, "trajectory.json"), "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "mode": "direct",
                    "meters_per_pixel": METERS_PER_PIXEL,
                    "blend": BLEND,
                    "sign_x": SIGN_X,
                    "sign_y": SIGN_Y,
                },
                "poses": poses,
            }, f, indent=4)
        safe_shutdown(h)


if __name__ == "__main__":
    main()

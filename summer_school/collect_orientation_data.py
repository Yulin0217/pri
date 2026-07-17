"""Collect orientation-label data for the pCLE probe.

With the rotation pivot at the probe tip, the probe is tilted to a grid of
(axis, angle) orientations. `axis` is the azimuth of the tilt direction in the
XY plane; `angle` is the tilt of the probe axis away from the surface normal.
Each orientation is converted to (dRx, dRy) with compute_dRx_dRy, the probe is
moved, and the pCLE live view is captured and labelled. The resulting
(image, axis, angle) pairs train the model that predicts the probe orientation
relative to the tissue surface -- the same `axis`/`angle` values the server
returns to apps/client.py during visual servoing.

Run:
    python summer_school/collect_orientation_data.py
"""

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
from common.utils_client import SmarPod_init, compute_dRx_dRy, pose_to_str
from summer_school.collection_utils import (
    PROBE_TIP_Z_M, prepare_probe, move_home, save_labels,
)

# ---- Configuration --------------------------------------------------------
AXIS_START_DEG = 0.0     # azimuth sweep start
AXIS_END_DEG = 180.0     # azimuth sweep end (inclusive)
AXIS_STEP_DEG = 30.0
ANGLE_MIN_DEG = -10.0    # tilt away from the surface normal
ANGLE_MAX_DEG = 10.0
ANGLE_STEP_DEG = 2.0
BASE_Z_UM = 0.0          # optional constant defocus applied during the sweep
RETURN_HOME_BETWEEN_AXES = True
FRAMES_PER_POSE = 1      # images captured at each orientation
SETTLE_S = 0.5           # settle time after each move, before capturing
# ---------------------------------------------------------------------------


def frange(start, stop, step):
    """Inclusive float range: start, start+step, ..., up to stop."""
    n = int(round((stop - start) / step))
    return [round(start + k * step, 3) for k in range(n + 1)]


def safe_shutdown(h):
    if h is None:
        return
    try:
        move_home(h)
        smarpod.Stop(h)
    finally:
        smarpod.Close(h)
        print("device closed")


def main():
    out_dir = time.strftime("orientation_data_%Y-%m-%d_%H-%M-%S")
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    axes = frange(AXIS_START_DEG, AXIS_END_DEG, AXIS_STEP_DEG)
    angles = frange(ANGLE_MIN_DEG, ANGLE_MAX_DEG, ANGLE_STEP_DEG)
    base_z_m = -abs(BASE_Z_UM) * 1e-6

    h = None
    records = []
    try:
        h = SmarPod_init()
        prepare_probe(h, PROBE_TIP_Z_M)

        print("\nManually bring the probe into best focus on the sample.")
        input("Press Enter to start the orientation sweep... ")

        idx = 0
        for axis in axes:
            for angle in angles:
                dRx, dRy = compute_dRx_dRy(angle=angle, axis=axis)
                pose = Pose(0.0, 0.0, base_z_m, dRx, dRy, 0.0)
                if not smarpod.IsPoseReachable(h, pose):
                    print("skip unreachable pose: axis=%.1f angle=%.1f" % (axis, angle))
                    continue

                smarpod.Move(h, pose, 0, True)
                time.sleep(SETTLE_S)

                for _ in range(FRAMES_PER_POSE):
                    image = capture_pcle_view(gray=True)
                    fname = "orient_%04d_ax%03.0f_an%+03.0f.png" % (idx, axis, angle)
                    cv2.imwrite(os.path.join(img_dir, fname), image)
                    records.append({
                        "file": os.path.join("images", fname),
                        "axis_deg": axis,
                        "angle_deg": angle,
                        "dRx_deg": dRx,
                        "dRy_deg": dRy,
                        "base_z_um": BASE_Z_UM,
                        "pose": pose_to_str(pose),
                    })
                    idx += 1
                print("captured axis=%6.1f angle=%+6.1f (%d frame(s))" % (axis, angle, FRAMES_PER_POSE))

            if RETURN_HOME_BETWEEN_AXES:
                move_home(h)
                time.sleep(SETTLE_S)

        move_home(h)
    except KeyboardInterrupt:
        print("\nInterrupted by user; saving collected data.")
    finally:
        metadata = {
            "type": "orientation",
            "axis_start_deg": AXIS_START_DEG,
            "axis_end_deg": AXIS_END_DEG,
            "axis_step_deg": AXIS_STEP_DEG,
            "angle_min_deg": ANGLE_MIN_DEG,
            "angle_max_deg": ANGLE_MAX_DEG,
            "angle_step_deg": ANGLE_STEP_DEG,
            "base_z_um": BASE_Z_UM,
            "frames_per_pose": FRAMES_PER_POSE,
            "probe_tip_z_m": PROBE_TIP_Z_M,
        }
        path = save_labels(out_dir, records, metadata)
        print("saved %d records to %s" % (len(records), path))
        safe_shutdown(h)


if __name__ == "__main__":
    main()

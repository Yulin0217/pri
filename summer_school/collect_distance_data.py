"""Collect distance-label data for the pCLE probe.

Starting from a user-set in-focus reference plane, the probe is translated along
Z in fixed steps. At each step the pCLE live view is captured and labelled with
the defocus distance (micrometres). The resulting (image, distance) pairs train
the model that predicts how far the probe is from the tissue surface -- the same
`distance` value the server returns to apps/client.py during visual servoing.

Run:
    python summer_school/collect_distance_data.py
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
from common.utils_client import SmarPod_init, pose_to_str
from summer_school.collection_utils import (
    PROBE_TIP_Z_M, prepare_probe, move_home, save_labels,
)

# ---- Configuration --------------------------------------------------------
Z_STEP_UM = 5.0          # step size along Z (micrometres)
Z_MAX_UM = 200.0         # maximum defocus distance from the focus plane
Z_DIRECTION = -1         # -1: move away along -Z (matches apps/client.py)
FRAMES_PER_STEP = 1      # images captured at each Z position
SETTLE_S = 0.5           # settle time after each move, before capturing
# ---------------------------------------------------------------------------


def build_distance_steps():
    """Distances (um) from the focus plane: 0, step, 2*step, ..., Z_MAX_UM."""
    n = int(round(Z_MAX_UM / Z_STEP_UM))
    return [round(k * Z_STEP_UM, 3) for k in range(n + 1)]


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
    out_dir = time.strftime("distance_data_%Y-%m-%d_%H-%M-%S")
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    h = None
    records = []
    try:
        h = SmarPod_init()
        prepare_probe(h, PROBE_TIP_Z_M)

        print("\nManually bring the probe into best focus on the sample.")
        print("This position is used as the zero-distance reference.")
        input("Press Enter when the probe is in focus... ")

        idx = 0
        for distance_um in build_distance_steps():
            z_m = Z_DIRECTION * distance_um * 1e-6
            pose = Pose(0.0, 0.0, z_m, 0.0, 0.0, 0.0)
            if not smarpod.IsPoseReachable(h, pose):
                print("skip unreachable distance = %.1f um" % distance_um)
                continue

            smarpod.Move(h, pose, 0, True)
            time.sleep(SETTLE_S)

            for _ in range(FRAMES_PER_STEP):
                image = capture_pcle_view(gray=True)
                fname = "dist_%04d_%03.0fum.png" % (idx, distance_um)
                cv2.imwrite(os.path.join(img_dir, fname), image)
                records.append({
                    "file": os.path.join("images", fname),
                    "distance_um": distance_um,
                    "z_offset_um": Z_DIRECTION * distance_um,
                    "pose": pose_to_str(pose),
                })
                idx += 1
            print("captured distance = %6.1f um (%d frame(s))" % (distance_um, FRAMES_PER_STEP))

        move_home(h)
    except KeyboardInterrupt:
        print("\nInterrupted by user; saving collected data.")
    finally:
        metadata = {
            "type": "distance",
            "z_step_um": Z_STEP_UM,
            "z_max_um": Z_MAX_UM,
            "z_direction": Z_DIRECTION,
            "frames_per_step": FRAMES_PER_STEP,
            "probe_tip_z_m": PROBE_TIP_Z_M,
        }
        path = save_labels(out_dir, records, metadata)
        print("saved %d records to %s" % (len(records), path))
        safe_shutdown(h)


if __name__ == "__main__":
    main()

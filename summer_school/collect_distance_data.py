"""Collect distance-label data for the pCLE probe.

Data is collected in groups. Before each group the user manually brings the
probe into best focus and presses Enter; the pose at that moment becomes the
zero-distance reference for the group. The probe is then translated along Z in
fixed steps from that reference, capturing the pCLE live view labelled with the
defocus distance (micrometres) at each step. After a group finishes the probe
returns to the group's zero reference so the user can refocus and start the
next group (q + Enter ends the session). The resulting (image, distance) pairs
train the model that predicts how far the probe is from the tissue surface --
the same `distance` value the server returns to apps/client.py during visual
servoing.

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
Z_STEP_UM = 10.0         # step size along Z (micrometres)
Z_MAX_UM = 200.0         # maximum defocus distance from the focus plane
Z_DIRECTION = -1         # -1: move away along -Z (matches apps/client.py)
FRAMES_PER_STEP = 1      # images captured at each Z position
SETTLE_S = 0.5           # settle time after each move, before capturing
# ---------------------------------------------------------------------------


def build_distance_steps():
    """Distances (um) from the focus plane: 0, step, 2*step, ..., Z_MAX_UM."""
    n = int(round(Z_MAX_UM / Z_STEP_UM))
    return [round(k * Z_STEP_UM, 3) for k in range(n + 1)]


def retract_from_sample(h):
    """Back the probe away from the sample along Z_DIRECTION before homing, so
    the home move cannot drag the tip laterally while still at contact height
    (the manually-set zero reference may include X/Y/tilt offsets)."""
    pose = smarpod.GetPose(h)
    target = Pose(
        pose.positionX,
        pose.positionY,
        pose.positionZ + Z_DIRECTION * Z_MAX_UM * 1e-6,
        pose.rotationX,
        pose.rotationY,
        pose.rotationZ,
    )
    if smarpod.IsPoseReachable(h, target):
        smarpod.Move(h, target, 0, True)


def safe_shutdown(h):
    if h is None:
        return
    try:
        retract_from_sample(h)
        move_home(h)
        smarpod.Stop(h)
    finally:
        smarpod.Close(h)
        print("device closed")


def collect_group(h, group, base, img_dir, records, idx):
    """Sweep 0..Z_MAX_UM below the group's zero-reference pose; return next idx."""
    for distance_um in build_distance_steps():
        pose = Pose(
            base.positionX,
            base.positionY,
            base.positionZ + Z_DIRECTION * distance_um * 1e-6,
            base.rotationX,
            base.rotationY,
            base.rotationZ,
        )
        if not smarpod.IsPoseReachable(h, pose):
            print("skip unreachable distance = %.1f um" % distance_um)
            continue

        smarpod.Move(h, pose, 0, True)
        time.sleep(SETTLE_S)

        for _ in range(FRAMES_PER_STEP):
            image = capture_pcle_view(gray=True)
            fname = "g%02d_dist_%04d_%03.0fum.png" % (group, idx, distance_um)
            cv2.imwrite(os.path.join(img_dir, fname), image)
            records.append({
                "file": os.path.join("images", fname),
                "group": group,
                "distance_um": distance_um,
                "z_offset_um": Z_DIRECTION * distance_um,
                "pose": pose_to_str(pose),
            })
            idx += 1
        print("captured distance = %6.1f um (%d frame(s))" % (distance_um, FRAMES_PER_STEP))
    return idx


def main():
    out_dir = time.strftime("distance_data_%Y-%m-%d_%H-%M-%S")
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    h = None
    records = []
    group = 0
    try:
        h = SmarPod_init()
        prepare_probe(h, PROBE_TIP_Z_M)

        idx = 0
        while True:
            print("\nManually bring the probe into best focus on the sample.")
            print("That position becomes the zero-distance reference for group %d." % group)
            cmd = input("Press Enter to start collecting (q + Enter to finish)... ").strip().lower()
            if cmd == "q":
                break

            base = smarpod.GetPose(h)
            print("group %d zero reference: %s" % (group, pose_to_str(base)))

            idx = collect_group(h, group, base, img_dir, records, idx)

            zero_pose = Pose(
                base.positionX, base.positionY, base.positionZ,
                base.rotationX, base.rotationY, base.rotationZ,
            )
            smarpod.Move(h, zero_pose, 0, True)
            print("group %d done; probe returned to its zero-reference position." % group)
            group += 1
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
            "groups": (max(r["group"] for r in records) + 1) if records else 0,
        }
        try:
            path = save_labels(out_dir, records, metadata)
            print("saved %d records to %s" % (len(records), path))
        finally:
            safe_shutdown(h)


if __name__ == "__main__":
    main()

"""Shared helpers for the summer-school data-collection scripts."""

import json
import os

import smaract.smarpod as smarpod
from smaract.smarpod import Pose

from common.utils_client import pose_to_str

# Pivot point at the probe tip: distance (m) from the SmarPod platform origin
# down to the tip. Calibrate for your hardware (see tools/robot_test.py).
PROBE_TIP_Z_M = 37.4e-3

HOME_POSE = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def prepare_probe(h, pivot_tip_z_m=PROBE_TIP_Z_M):
    """Reset the coordinate system to the origin, put the rotation pivot at the
    probe tip, and move home so that later tilts keep the tip fixed in space."""
    csys = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    smarpod.SetCoordinateSystem(h, csys)
    smarpod.SetPivot(h, [0.0, 0.0, pivot_tip_z_m])
    print("coordinate system set to %s" % pose_to_str(csys))
    print("pivot point set to %s" % smarpod.GetPivot(h))
    move_home(h)


def move_home(h):
    """Move the probe back to the home pose (all zeros)."""
    smarpod.Move(h, HOME_POSE, 0, True)


def save_labels(out_dir, records, metadata):
    """Write collected labels to <out_dir>/labels.json and return the path."""
    path = os.path.join(out_dir, "labels.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "records": records}, f, indent=4)
    return path

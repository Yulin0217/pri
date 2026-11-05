"""Collect tilt-labelled frames as Euler-component offsets from a focus reference.

The original tilt conversion is preserved. Its dRx/dRy values are added to
controller rotations at the manually focused pose, rather than replacing the
reference XYZ and rotations with zero. This is not general SO(3) composition.
"""

import math
import time

from smarpod_pcle.capture import capture_pcle_view
from smarpod_pcle.config import get_settings
from smarpod_pcle.hardware import (
    SmarPod_init, compute_dRx_dRy, get_sdk, move_checked, pose_to_str, shutdown,
)
from smarpod_pcle.output import create_run_dir, save_image
from .common import inclusive_steps, prepare_probe, save_labels, validate_capture_parameters

AXIS_START_DEG = 0.0
AXIS_END_DEG = 180.0
AXIS_STEP_DEG = 30.0
ANGLE_MIN_DEG = -10.0
ANGLE_MAX_DEG = 10.0
ANGLE_STEP_DEG = 2.0
BASE_Z_UM = 0.0
RETURN_HOME_BETWEEN_AXES = True  # Historical name: now returns to the focus reference.
FRAMES_PER_POSE = 1
SETTLE_S = 0.5


def frange(start, stop, step):
    return inclusive_steps(start, stop, step)


def main():
    axes = frange(AXIS_START_DEG, AXIS_END_DEG, AXIS_STEP_DEG)
    angles = frange(ANGLE_MIN_DEG, ANGLE_MAX_DEG, ANGLE_STEP_DEG)
    validate_capture_parameters(FRAMES_PER_POSE, SETTLE_S)
    if not math.isfinite(BASE_Z_UM):
        raise ValueError("BASE_Z_UM must be finite")
    sdk = get_sdk()
    pivot_z = get_settings().robot.probe_tip_z_m
    out_dir = create_run_dir("orientation_data")
    img_dir = out_dir / "images"
    img_dir.mkdir()
    handle = None
    records = []
    base = None
    try:
        handle = SmarPod_init()
        prepare_probe(handle, pivot_z)
        print("Manually focus the probe; the current pose becomes the orientation reference.")
        input("Press Enter to start the orientation sweep: ")
        base = sdk.GetPose(handle)
        idx = 0
        for axis in axes:
            for angle in angles:
                rx, ry = compute_dRx_dRy(angle=angle, axis=axis)
                pose = sdk.Pose(
                    base.positionX, base.positionY, base.positionZ - abs(BASE_Z_UM) * 1e-6,
                    base.rotationX + rx, base.rotationY + ry, base.rotationZ,
                )
                if not sdk.IsPoseReachable(handle, pose):
                    print(f"Skipping unreachable orientation: axis={axis:.1f}, angle={angle:.1f}")
                    continue
                move_checked(handle, pose)
                time.sleep(SETTLE_S)
                for _ in range(FRAMES_PER_POSE):
                    filename = f"orient_{idx:04d}_ax{axis:03.0f}_an{angle:+03.0f}.png"
                    save_image(img_dir / filename, capture_pcle_view())
                    records.append({
                        "file": f"images/{filename}", "axis_deg": axis, "angle_deg": angle,
                        "dRx_deg": rx, "dRy_deg": ry, "base_z_um": BASE_Z_UM,
                        "pose": pose_to_str(pose),
                    })
                    idx += 1
                print(f"Captured axis={axis:.1f}, angle={angle:+.1f}")
            if RETURN_HOME_BETWEEN_AXES:
                move_checked(handle, base)
                time.sleep(SETTLE_S)
        move_checked(handle, base)
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted; stopping at the current pose and saving completed frames.")
    finally:
        metadata = {
            "type": "orientation", "axis_start_deg": AXIS_START_DEG, "axis_end_deg": AXIS_END_DEG,
            "axis_step_deg": AXIS_STEP_DEG, "angle_min_deg": ANGLE_MIN_DEG,
            "angle_max_deg": ANGLE_MAX_DEG, "angle_step_deg": ANGLE_STEP_DEG,
            "base_z_um": BASE_Z_UM, "frames_per_pose": FRAMES_PER_POSE,
            "probe_tip_z_m": pivot_z,
            "reference_pose": pose_to_str(base) if base is not None else None,
            "rotation_convention": "additive_controller_euler_offsets",
        }
        try:
            path = save_labels(out_dir, records, metadata)
            print(f"Saved {len(records)} records to {path}")
        finally:
            shutdown(handle)


if __name__ == "__main__":
    main()

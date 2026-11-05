"""Collect distance-labelled frames relative to a manually focused pose per group."""

from pathlib import Path
import time

from smarpod_pcle.capture import capture_pcle_view
from smarpod_pcle.config import get_settings
from smarpod_pcle.hardware import SmarPod_init, get_sdk, move_checked, pose_to_str, shutdown
from smarpod_pcle.output import create_run_dir, save_image
from .common import inclusive_steps, prepare_probe, save_labels, validate_capture_parameters

Z_STEP_UM = 10.0
Z_MAX_UM = 200.0
Z_DIRECTION = -1
FRAMES_PER_STEP = 1
SETTLE_S = 0.5


def build_distance_steps():
    """Grid distances from zero up to, but never beyond, Z_MAX_UM."""
    return inclusive_steps(0.0, Z_MAX_UM, Z_STEP_UM)


def collect_group(handle, group, base, img_dir, records, idx):
    """Capture a sweep while retaining the group's XY and orientation reference."""
    sdk = get_sdk()
    for distance_um in build_distance_steps():
        pose = sdk.Pose(
            base.positionX, base.positionY,
            base.positionZ + Z_DIRECTION * distance_um * 1e-6,
            base.rotationX, base.rotationY, base.rotationZ,
        )
        if not sdk.IsPoseReachable(handle, pose):
            print(f"Skipping unreachable distance: {distance_um:.1f} um")
            continue
        move_checked(handle, pose)
        time.sleep(SETTLE_S)
        for _ in range(FRAMES_PER_STEP):
            filename = f"g{group:02d}_dist_{idx:04d}_{distance_um:03.0f}um.png"
            save_image(Path(img_dir) / filename, capture_pcle_view())
            records.append({
                "file": f"images/{filename}",
                "group": group,
                "distance_um": distance_um,
                "z_offset_um": Z_DIRECTION * distance_um,
                "pose": pose_to_str(pose),
            })
            idx += 1
        print(f"Captured distance {distance_um:6.1f} um ({FRAMES_PER_STEP} frame(s))")
    return idx


def main():
    build_distance_steps()
    validate_capture_parameters(FRAMES_PER_STEP, SETTLE_S)
    if type(Z_DIRECTION) is not int or Z_DIRECTION not in (-1, 1):
        raise ValueError("Z_DIRECTION must be -1 or 1")
    sdk = get_sdk()
    pivot_z = get_settings().robot.probe_tip_z_m
    out_dir = create_run_dir("distance_data")
    img_dir = out_dir / "images"
    img_dir.mkdir()
    handle = None
    records = []
    references = []
    group = 0
    try:
        handle = SmarPod_init()
        prepare_probe(handle, pivot_z)
        idx = 0
        while True:
            print(f"Manually focus the probe for group {group}; its current pose becomes zero distance.")
            command = input("Enter to collect; q to finish: ").strip().lower()
            if command == "q":
                break
            base = sdk.GetPose(handle)
            references.append({"group": group, "pose": pose_to_str(base)})
            idx = collect_group(handle, group, base, img_dir, records, idx)
            move_checked(handle, base)
            print(f"Group {group} complete; returned to its focus reference.")
            group += 1
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted; stopping at the current pose and saving completed frames.")
    finally:
        metadata = {
            "type": "distance", "z_step_um": Z_STEP_UM, "z_max_um": Z_MAX_UM,
            "z_direction": Z_DIRECTION, "frames_per_step": FRAMES_PER_STEP,
            "probe_tip_z_m": pivot_z,
            "groups": len(references), "reference_poses": references,
        }
        try:
            path = save_labels(out_dir, records, metadata)
            print(f"Saved {len(records)} records to {path}")
        finally:
            shutdown(handle)


if __name__ == "__main__":
    main()

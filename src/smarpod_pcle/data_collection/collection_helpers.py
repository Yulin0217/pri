"""Shared collection setup, validated ranges and label persistence."""

from decimal import Decimal
import json
import math
from pathlib import Path

from smarpod_pcle.config import get_settings
from smarpod_pcle.robot_control import get_sdk, move_checked, pose_to_str


def prepare_probe(handle, pivot_tip_z_m=None):
    """Set the coordinate system and tip pivot without an automatic home move.

    Pivot coordinates are metres. The collector records the actual focus pose
    after the operator finishes positioning; coordinate zero is not assumed to
    be the sample's focus plane.
    """
    sdk = get_sdk()
    if pivot_tip_z_m is None:
        pivot_tip_z_m = get_settings().robot.probe_tip_z_m
    origin = sdk.Pose(0, 0, 0, 0, 0, 0)
    sdk.SetCoordinateSystem(handle, origin)
    sdk.SetPivot(handle, [0.0, 0.0, pivot_tip_z_m])
    print(f"Coordinate system: {pose_to_str(origin)}; tip pivot Z: {pivot_tip_z_m} m")


def move_home(handle):
    """Explicitly move to coordinate zero; never invoked by error cleanup."""
    move_checked(handle, get_sdk().Pose(0, 0, 0, 0, 0, 0))


def inclusive_steps(start, stop, step):
    """Return ascending samples including stop only when it lies on the grid.

    Decimal arithmetic avoids rounding the final step above the requested limit.
    """
    if any(isinstance(value, bool) or not math.isfinite(value) for value in (start, stop, step)):
        raise ValueError("Range values must be finite numbers")
    if step <= 0 or stop < start:
        raise ValueError("Range step must be positive and stop must be >= start")
    first, last, increment = (Decimal(str(value)) for value in (start, stop, step))
    count = int((last - first) // increment)
    return [float(first + index * increment) for index in range(count + 1)]


def validate_capture_parameters(frames, settle_s):
    if type(frames) is not int or frames <= 0:
        raise ValueError("Frames per pose must be a positive integer")
    if not math.isfinite(settle_s) or settle_s < 0:
        raise ValueError("Settle time must be finite and nonnegative")


def save_labels(out_dir, records, metadata):
    """Persist completed image records and the reference needed to interpret them."""
    path = Path(out_dir) / "labels.json"
    with path.open("w", encoding="utf-8") as stream:
        json.dump({"metadata": metadata, "records": records}, stream, indent=4)
    return path

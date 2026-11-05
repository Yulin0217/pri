"""SDK-independent coordinate helpers (translations in metres, rotations in degrees)."""

import math


def compute_dRx_dRy(angle, axis):
    """Preserve the original small-angle tilt projection used by the trained model.

    This is not a general exact Euler decomposition of arbitrary 3D rotations.
    """
    angle, axis = math.radians(angle), math.radians(axis)
    return (math.degrees(math.asin(math.sin(angle) * math.cos(axis))),
            math.degrees(math.asin(math.sin(angle) * math.sin(axis))))


def pose_to_str(pose):
    return ",".join(str(getattr(pose, name)) for name in (
        "positionX", "positionY", "positionZ", "rotationX", "rotationY", "rotationZ"
    ))

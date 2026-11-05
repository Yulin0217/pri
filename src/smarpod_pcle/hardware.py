"""Vendor SDK boundary. Importing this module does not load or open a controller."""

from importlib import import_module
import math
from .config import get_settings
from .geometry import compute_dRx_dRy, pose_to_str  # noqa: F401 -- compatibility exports


def get_sdk():
    try:
        return import_module("smaract.smarpod")
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "Install the matching SmarAct SmarPod Python API and native runtime on the "
            "control computer. See docs/portability.md; the SDK is not a pip dependency."
        ) from exc


def check_lib_compatibility():
    sdk = get_sdk()
    if sdk.api_version[0] != sdk.GetDLLVersion()[0]:
        raise RuntimeError("Incompatible SmarPod Python API and native library major versions")


def print_info():
    sdk = get_sdk()
    print(f"API version: {sdk.api_version}; native library: {sdk.GetDLLVersion()}")


def print_controllers():
    print(get_sdk().FindSystems())


def shutdown(handle):
    """Stop and close even if Stop fails. Never add a return-home move on errors."""
    if handle is not None:
        sdk = get_sdk()
        try:
            sdk.Stop(handle)
        finally:
            sdk.Close(handle)


def move_checked(handle, pose):
    sdk = get_sdk()
    values = (pose.positionX, pose.positionY, pose.positionZ,
              pose.rotationX, pose.rotationY, pose.rotationZ)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Refusing a non-finite robot pose")
    if not sdk.IsPoseReachable(handle, pose):
        raise ValueError(f"Unreachable robot pose: {pose_to_str(pose)}")
    sdk.Move(handle, pose, 0, True)


def check_pose_list(handle, poses):
    return all(get_sdk().IsPoseReachable(handle, pose) for pose in poses)


def move_sequence(handle, poses):
    for pose in poses:
        move_checked(handle, pose)


def SmarPod_init():
    """Explicit hardware startup: calibration/reference operations may move the stage."""
    sdk = get_sdk()
    check_lib_compatibility()
    print_info()
    cfg = get_settings().robot
    calibrate = input("Calibrate sensors? 0: no, 1: yes ==> ").strip() == "1"
    handle = sdk.Open(cfg.model, cfg.locator)
    try:
        sdk.Set_ui(handle, sdk.Property.FREF_AND_CAL_FREQUENCY, 8000)
        if calibrate:
            sdk.Calibrate(handle)
        if not sdk.IsReferenced(handle):
            sdk.Set_ui(handle, sdk.Property.FREF_METHOD, sdk.DEFAULT)
            sdk.FindReferenceMarks(handle)
        sdk.SetSensorMode(handle, sdk.SensorPowerMode.ENABLED)
        sdk.Stop(handle)
        sdk.SetSpeed(handle, 1, cfg.speed_m_s)
        sdk.SetMaxFrequency(handle, cfg.max_frequency_hz)
        sdk.Set_ui(handle, sdk.Property.PIVOT_MODE, sdk.PivotMode.RELATIVE)
    except BaseException:
        shutdown(handle)
        raise
    return handle

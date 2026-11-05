"""Regression checks for historical entry points without robot hardware."""

import builtins
import importlib
import json
from pathlib import Path
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import cv2  # noqa: F401 -- preload extension modules before restoring sys.modules.

from smarpod_pcle.scan_experiments import xy_grid_capture as data_collection
from smarpod_pcle.interactive_tools import z_axis_jog as manual_z_step_control


def fake_modules():
    sdk = ModuleType("smaract.smarpod")
    sdk.Pose = lambda *values: SimpleNamespace(**dict(zip(
        ("positionX", "positionY", "positionZ", "rotationX", "rotationY", "rotationZ"),
        values,
    )))
    sdk.SetPivot = Mock()
    sdk.SetCoordinateSystem = Mock()
    sdk.GetPose = Mock(return_value=sdk.Pose(0, 0, 0, 0, 0, 0))
    sdk.IsPoseReachable = Mock(return_value=True)
    package = ModuleType("smaract")
    package.smarpod = sdk
    hardware = ModuleType("smarpod_pcle.robot_control")
    hardware.SmarPod_init = Mock(return_value="handle")
    hardware.move_checked = Mock()
    hardware.pose_to_str = Mock(return_value="0,0,0,0,0,0")
    hardware.shutdown = Mock()
    return {"smaract": package, "smaract.smarpod": sdk, "smarpod_pcle.robot_control": hardware}


class LegacyTests(unittest.TestCase):
    def test_imports_never_load_sdk_or_prompt(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith("smaract") or name == "smarpod_pcle.robot_control":
                self.fail(f"Import attempted hardware access: {name}")
            return original_import(name, *args, **kwargs)

        modules = (
            "scan_experiments.xy_grid_capture", "scan_experiments.xy_cross_scan",
            "data_collection.spiral_capture", "interactive_tools.z_axis_jog", "interactive_tools.probe_pivot_check",
            "interactive_tools.screen_region_preview", "sdk_examples.pose_sequence", "sdk_examples.configure_controller",
        )
        with patch("builtins.__import__", side_effect=guarded_import), \
             patch("builtins.input", side_effect=AssertionError("Prompt during import")):
            for name in modules:
                with self.subTest(module=name):
                    importlib.reload(importlib.import_module(f"smarpod_pcle.{name}"))

    def test_grid_records_every_image_and_keeps_z_zero(self):
        samples = list(data_collection.grid_samples())
        self.assertEqual(len(samples), 21 * 21 * 41)
        self.assertTrue(all(xyz[2] == 0 for _, _, _, xyz in samples))
        modules = fake_modules()
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict("sys.modules", modules), \
             patch("builtins.input", return_value=""), \
             patch("smarpod_pcle.run_output.create_run_dir", return_value=Path(temp)), \
             patch("smarpod_pcle.screen_capture.capture_pcle_view", return_value=None), \
             patch("cv2.imwrite", return_value=True), \
             patch.object(data_collection, "grid_samples", return_value=iter(samples[:2])):
            data_collection.main()
            records = json.loads((Path(temp) / "trajectory.json").read_text())
            self.assertEqual(list(records), ["0", "1"])
        modules["smarpod_pcle.robot_control"].shutdown.assert_called_once_with("handle")

    def test_grid_write_failure_still_closes_robot(self):
        modules = fake_modules()
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict("sys.modules", modules), \
             patch("builtins.input", return_value=""), \
             patch("smarpod_pcle.run_output.create_run_dir", return_value=Path(temp)), \
             patch("smarpod_pcle.screen_capture.capture_pcle_view", return_value=None), \
             patch("cv2.imwrite", return_value=False), \
             self.assertRaises(OSError):
            data_collection.main()
        modules["smarpod_pcle.robot_control"].shutdown.assert_called_once_with("handle")

    def test_unrecognized_jog_input_does_not_move(self):
        modules = fake_modules()
        with patch.dict("sys.modules", modules), \
             patch("builtins.input", side_effect=["typo", "q"]):
            manual_z_step_control.main()
        modules["smarpod_pcle.robot_control"].move_checked.assert_not_called()
        modules["smarpod_pcle.robot_control"].shutdown.assert_called_once_with("handle")


if __name__ == "__main__":
    unittest.main()

"""Collection regressions: real focus references and failure-safe cleanup."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from smarpod_pcle.collection import distance, orientation
from smarpod_pcle.collection.common import inclusive_steps


def pose(*values):
    return SimpleNamespace(**dict(zip(
        ("positionX", "positionY", "positionZ", "rotationX", "rotationY", "rotationZ"),
        values,
    )))


class CollectionTests(unittest.TestCase):
    def set_up_run(self, stack, module, base, inputs):
        output = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        sdk = SimpleNamespace(Pose=pose, GetPose=Mock(return_value=base),
                              IsPoseReachable=Mock(return_value=True))
        stack.enter_context(patch.object(module, "get_sdk", return_value=sdk))
        stack.enter_context(patch.object(module, "SmarPod_init", return_value="handle"))
        stack.enter_context(patch.object(module, "prepare_probe"))
        stack.enter_context(patch.object(module, "create_run_dir", return_value=output))
        stack.enter_context(patch.object(module, "capture_pcle_view", return_value=None))
        stack.enter_context(patch.object(module, "SETTLE_S", 0))
        stack.enter_context(patch("builtins.input", side_effect=inputs))
        mocks = {name: stack.enter_context(patch.object(module, name)) for name in
                 ("move_checked", "save_image", "save_labels", "shutdown")}
        return sdk, mocks

    def test_ranges_never_overshoot_limits(self):
        self.assertEqual(inclusive_steps(0, 20, 6), [0, 6, 12, 18])
        self.assertEqual(inclusive_steps(-0.3, 0.3, 0.1), [-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3])
        for arguments in ((0, 10, 0), (0, 10, -1), (0, -1, 1), (0, float("inf"), 1)):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                inclusive_steps(*arguments)

    def test_orientation_uses_manually_focused_pose(self):
        base = pose(0.003, 0.004, -0.002, 1, 2, 3)
        with ExitStack() as stack:
            _, mocks = self.set_up_run(stack, orientation, base, [""])
            stack.enter_context(patch.object(orientation, "frange", side_effect=[[0], [2]]))
            stack.enter_context(patch.object(orientation, "BASE_Z_UM", 20))
            orientation.main()
            target = mocks["move_checked"].call_args_list[0].args[1]
            self.assertEqual((target.positionX, target.positionY), (0.003, 0.004))
            self.assertAlmostEqual(target.positionZ, -0.00202)
            self.assertAlmostEqual(target.rotationX, 3)
            self.assertAlmostEqual(target.rotationY, 2)
            self.assertAlmostEqual(target.rotationZ, 3)
            self.assertIs(mocks["move_checked"].call_args.args[1], base)
            _, records, metadata = mocks["save_labels"].call_args.args
            self.assertEqual(len(records), 1)
            self.assertEqual(metadata["reference_pose"], "0.003,0.004,-0.002,1,2,3")
            mocks["shutdown"].assert_called_once_with("handle")

    def test_distance_references_are_preserved_per_group(self):
        first = pose(0.001, 0.002, -0.003, 1, 2, 3)
        second = pose(0.004, 0.005, -0.006, 4, 5, 6)
        with ExitStack() as stack:
            sdk, mocks = self.set_up_run(stack, distance, first, ["", "", "q"])
            sdk.GetPose.side_effect = [first, second]
            stack.enter_context(patch.object(distance, "build_distance_steps", return_value=[0, 10]))
            distance.main()
            targets = [call.args[1] for call in mocks["move_checked"].call_args_list]
            self.assertEqual(targets[1].positionX, first.positionX)
            self.assertAlmostEqual(targets[1].positionZ, first.positionZ - 10e-6)
            self.assertIs(targets[2], first)
            self.assertEqual(targets[4].positionX, second.positionX)
            self.assertAlmostEqual(targets[4].positionZ, second.positionZ - 10e-6)
            self.assertIs(targets[5], second)
            _, records, metadata = mocks["save_labels"].call_args.args
            self.assertEqual([record["group"] for record in records], [0, 0, 1, 1])
            self.assertEqual(len(metadata["reference_poses"]), 2)
            mocks["shutdown"].assert_called_once_with("handle")

    def test_collection_failures_stop_without_home(self):
        base = pose(0.001, 0.002, -0.003, 1, 2, 3)
        for module in (distance, orientation):
            with self.subTest(module=module.__name__), ExitStack() as stack:
                _, mocks = self.set_up_run(stack, module, base, [""])
                mocks["save_image"].side_effect = OSError("disk full")
                mocks["save_labels"].side_effect = OSError("metadata write failed")
                with self.assertRaises(OSError):
                    module.main()
                # Exactly one scan move; cleanup must not issue any home/reference move.
                mocks["move_checked"].assert_called_once()
                mocks["shutdown"].assert_called_once_with("handle")


if __name__ == "__main__":
    unittest.main()

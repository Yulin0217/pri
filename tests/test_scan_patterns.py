"""Offline coverage geometry and CLI dispatch checks for alternative scans."""

import contextlib
import io
import json
import math
import unittest
from unittest.mock import Mock, patch

from smarpod_pcle import cli
from smarpod_pcle.mosaicking.scan_patterns import build_trajectory, main


class PatternTests(unittest.TestCase):
    def test_separate_commands(self):
        for pattern in ("serpentine", "raster", "rings"):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cli.main([f"mosaic-{pattern}", "--dry-run"]), 0)
            self.assertEqual(json.loads(output.getvalue())["scan"]["pattern"], pattern)

    def test_bounds_and_consecutive_spacing(self):
        for pattern in ("serpentine", "raster", "rings"):
            points = build_trajectory(pattern, width_m=0.0013, height_m=0.0007)
            self.assertTrue(points)
            for a, b in zip(points, points[1:]):
                self.assertLessEqual(math.dist(a, b), 0.0001 + 1e-12)
            for x, y in points:
                if pattern == "rings":
                    self.assertLessEqual(math.hypot(x, y), 0.0008 + 1e-12)
                else:
                    self.assertLessEqual(abs(x), 0.00065 + 1e-12)
                    self.assertLessEqual(abs(y), 0.00035 + 1e-12)

    def test_serpentine_order_and_full_grid(self):
        points = build_trajectory("serpentine", width_m=2, height_m=2, spacing_m=1)
        self.assertEqual(points, [(-1, -1), (0, -1), (1, -1),
                                  (1, 0), (0, 0), (-1, 0),
                                  (-1, 1), (0, 1), (1, 1)])

    def test_invalid_and_excessive_paths(self):
        for spacing in (0, -1, float("nan"), float("inf"), 1e-300):
            with self.assertRaises(ValueError):
                build_trajectory("rings", spacing_m=spacing)
        with self.assertRaises(ValueError):
            build_trajectory("unknown")

    def test_cli_dry_run_does_not_load_hardware(self):
        with patch("smarpod_pcle.mosaicking.scan_runner.get_sdk") as sdk, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["mosaic-scan", "--pattern", "rings", "--dry-run"]), 0)
        sdk.assert_not_called()
        result = json.loads(output.getvalue())
        self.assertEqual(result["scan"]["pattern"], "rings")
        self.assertEqual(result["waypoints_m"][0], [0, 0])

    def test_hardware_dispatch_receives_path_and_metadata(self):
        runner = Mock()
        with patch("smarpod_pcle.mosaicking.scan_runner.run_scan", runner):
            main(pattern="raster", regression=True)
        args = runner.call_args.kwargs
        self.assertTrue(args["regression"])
        self.assertEqual(args["scan_metadata"]["pattern"], "raster")
        self.assertEqual(args["trajectory"], build_trajectory("raster"))

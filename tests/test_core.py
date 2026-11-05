"""Hardware-free regressions for portability, framing, and mosaic geometry."""

from dataclasses import replace
import json
import math
import os
from pathlib import Path
import pickle
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from smarpod_pcle import config, geometry, net
from smarpod_pcle.mosaicking import core, regression, scan


class FragmentedSocket:
    """Deterministically split even the four-byte header into separate reads."""

    def __init__(self, data, fragment_size=1):
        self.data = data
        self.fragment_size = fragment_size

    def recv(self, size):
        count = min(size, self.fragment_size)
        part, self.data = self.data[:count], self.data[count:]
        return part


class ProtocolTests(unittest.TestCase):
    def test_fragmented_messages_preserve_boundaries(self):
        messages = [{"distance": 1.5, "angle": 0, "axis": 45}, {"signal": 1}]
        payloads = [pickle.dumps(message) for message in messages]
        sock = FragmentedSocket(b"".join(struct.pack("!I", len(body)) + body for body in payloads))
        self.assertEqual(net.recv_message(sock), messages[0])
        self.assertEqual(net.recv_message(sock), messages[1])

    def test_truncated_payload_fails_instead_of_hanging(self):
        sock = FragmentedSocket(struct.pack("!I", 100) + b"partial")
        with self.assertRaises(ConnectionError):
            net.recv_message(sock)

    def test_rejects_zero_and_oversized_frames_before_payload_read(self):
        for length in (0, net.MAX_MESSAGE_BYTES + 1):
            with self.subTest(length=length):
                sock = Mock()
                sock.recv.return_value = struct.pack("!I", length)
                with self.assertRaises(ValueError):
                    net.recv_message(sock)
                sock.recv.assert_called_once_with(4)

    def test_send_framing_and_image_encoding(self):
        message = net.encode_frame(np.full((32, 16), 80, np.uint8), signal=0)
        self.assertEqual(message["signal"], 0)
        self.assertTrue(message["image"].startswith(b"\xff\xd8"))
        sock = Mock()
        net.send_message(sock, message)
        packet = sock.sendall.call_args.args[0]
        self.assertEqual(struct.unpack("!I", packet[:4])[0], len(packet) - 4)
        self.assertEqual(pickle.loads(packet[4:]), message)


class ConfigurationTests(unittest.TestCase):
    def test_explicit_config_overrides_environment_and_resolves_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "machine.toml"
            path.write_text('output_dir = "datasets"\n[server]\nhost = "example.local"\n', encoding="utf-8")
            with patch.dict(os.environ, {"SMARPOD_PCLE_CONFIG": str(path.with_name("missing.toml"))}):
                settings = config.load_settings(path)
            self.assertEqual(settings.server.host, "example.local")
            self.assertEqual(settings.server.port, 12334)
            self.assertEqual(settings.output_dir, str((Path(temporary) / "datasets").resolve()))

    def test_environment_config_is_used_when_no_explicit_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "machine.toml"
            path.write_text('[robot]\nlocator = "usb:sn:123"\n', encoding="utf-8")
            with patch.dict(os.environ, {"SMARPOD_PCLE_CONFIG": str(path)}):
                self.assertEqual(config.load_settings().robot.locator, "usb:sn:123")

    def test_misspelled_or_invalid_config_is_rejected(self):
        invalid_documents = (
            '[robot]\nlocatr = "usb:ix:0"\n',
            '[server]\nport = 65536\n',
            '[server]\ntimeout_s = 0\n',
            '[robot]\nspeed_m_s = nan\n',
            '[mosaic]\nsign_x = true\n',
            '[capture.pcle_view]\ntop = 0\nleft = 0\nwidth = -1\nheight = 10\n',
            'output_dir = 12\n',
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.toml"
            for document in invalid_documents:
                with self.subTest(document=document):
                    path.write_text(document, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        config.load_settings(path)


class GeometryTests(unittest.TestCase):
    def test_tilt_projection_principal_axes_and_signs(self):
        for angle in (-10, 0, 10):
            with self.subTest(angle=angle):
                rx, ry = geometry.compute_dRx_dRy(angle, 0)
                self.assertAlmostEqual(rx, angle)
                self.assertAlmostEqual(ry, 0)
                rx, ry = geometry.compute_dRx_dRy(angle, 90)
                self.assertAlmostEqual(rx, 0)
                self.assertAlmostEqual(ry, angle)

    def test_spiral_join_has_no_radial_gap(self):
        trajectory = core.build_spiral_trajectory(coarse_step=0.3, fine_step=0.08)
        radii = [math.hypot(x, y) / 1e-4 for x, y in trajectory]
        final_coarse = next(index for index, radius in enumerate(radii) if math.isclose(radius, 4.8))
        self.assertAlmostEqual(radii[final_coarse + 1] - radii[final_coarse], 0.08)
        self.assertTrue(all(b > a for a, b in zip(radii, radii[1:])))


class MosaicTests(unittest.TestCase):
    def test_canvas_size_contains_asymmetric_trajectory(self):
        trajectory = [(0.0, 0.0), (10.0, 2.0)]
        image = np.ones((4, 6), np.uint8)
        height, width = core.estimate_canvas_size(trajectory, 1.0, image.shape, margin_px=0)
        canvas = core.MosaicCanvas(height, width, 1.0)
        for x, y in trajectory:
            canvas.place_meters(image, x, y)
        self.assertEqual(canvas.weight.sum(), image.size * len(trajectory))

    def test_clipping_keeps_corresponding_frame_pixels(self):
        canvas = core.MosaicCanvas(4, 4, 1.0, blend="overwrite")
        image = np.arange(16, dtype=np.uint8).reshape(4, 4)
        self.assertTrue(canvas.place_center_px(image, 3, 0))
        np.testing.assert_array_equal(canvas.render()[:, 3], image[:, 0])
        self.assertFalse(canvas.place_center_px(image, 10, 0))

    def test_overlap_blending_modes(self):
        first = np.full((2, 2), 20, np.uint8)
        second = np.full((2, 2), 10, np.uint8)
        for blend, expected in (("average", 15), ("max", 20), ("overwrite", 10)):
            with self.subTest(blend=blend):
                canvas = core.MosaicCanvas(4, 4, 1.0, blend=blend)
                canvas.place_center_px(first, 0, 0)
                canvas.place_center_px(second, 0, 0)
                np.testing.assert_array_equal(canvas.render()[1:3, 1:3], expected)

    def test_stage_y_axis_maps_up_in_image(self):
        canvas = core.MosaicCanvas(10, 10, 1.0)
        canvas.place_meters(np.ones((2, 2), np.uint8), 2, 2)
        self.assertEqual(canvas.render()[2:4, 6:8].sum(), 4)


class RegressionTests(unittest.TestCase):
    def test_first_frame_is_sent_as_reference(self):
        source = regression.DisplacementSource()
        source.sock = Mock()
        with patch.object(regression, "query_displacement", side_effect=[(99, 99), (3, -2)]) as query:
            self.assertEqual(source.offset(None, None, (0, 0)), (0.0, 0.0, "reference"))
            self.assertEqual(source.offset(None, (0, 0), (1e-6, 1e-6)), (3, -2, "regression"))
        self.assertEqual(query.call_count, 2)

    def test_failed_stream_is_closed_and_never_reused(self):
        failures = (pickle.UnpicklingError("invalid pickle"), ValueError("nan"),
                    OverflowError("int too large"), ConnectionError("closed"))
        for failure in failures:
            with self.subTest(failure=failure):
                source = regression.DisplacementSource()
                sock = source.sock = Mock()
                settings = config.Settings(mosaic=replace(config.MosaicSettings(), sign_x=-1))
                with patch.object(regression, "query_displacement", side_effect=failure) as query, \
                     patch.object(regression, "get_settings", return_value=settings):
                    dx, dy, origin = source.offset(None, (0, 0), (2e-6, 3e-6))
                    self.assertAlmostEqual(dx, -2)
                    self.assertAlmostEqual(dy, -3)
                    self.assertEqual(origin, "fallback")
                    source.offset(None, (2e-6, 3e-6), (3e-6, 4e-6))
                sock.close.assert_called_once()
                query.assert_called_once()
                self.assertIsNone(source.sock)

    def test_unavailable_server_uses_commanded_positions(self):
        source = regression.DisplacementSource()
        with patch.object(regression, "get_settings", return_value=config.Settings()):
            with patch.object(regression.socket, "create_connection", side_effect=OSError("offline")):
                source.connect()
            self.assertEqual(source.offset(None, None, (0, 0)), (0.0, 0.0, "reference"))
            self.assertEqual(source.offset(None, (0, 0), (1e-6, 0)), (1.0, 0.0, "fallback"))

    def test_query_validates_reply_and_converts_micrometres(self):
        settings = config.Settings(mosaic=replace(config.MosaicSettings(),
                                                 meters_per_pixel=2e-6,
                                                 regression_in_micrometers=True))
        with patch.object(regression, "encode_frame", return_value={}), \
             patch.object(regression, "send_message"), \
             patch.object(regression, "get_settings", return_value=settings), \
             patch.object(regression, "recv_message", return_value={"dx": 10, "dy": -4}) as receive:
            self.assertEqual(regression.query_displacement(Mock(), None), (5.0, -2.0))
            for reply in ([1, 2], {"dx": float("nan"), "dy": 0}):
                receive.return_value = reply
                with self.assertRaises(ValueError):
                    regression.query_displacement(Mock(), None)


class ScanLifecycleTests(unittest.TestCase):
    def test_image_save_failure_stops_hardware_before_final_save(self):
        events = []
        sdk = Mock()
        sdk.Pose.side_effect = lambda *values: tuple(values)
        sdk.IsPoseReachable.return_value = True
        image = np.ones((2, 2), np.uint8)
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(scan, "get_sdk", return_value=sdk), \
             patch.object(scan, "create_run_dir", return_value=Path(temporary)), \
             patch.object(scan, "SmarPod_init", return_value="fake-handle"), \
             patch.object(scan, "move_checked") as move, \
             patch.object(scan, "shutdown", side_effect=lambda handle: events.append(("shutdown", handle))), \
             patch.object(scan, "build_spiral_trajectory", return_value=[(1e-6, 0.0)]), \
             patch.object(scan, "capture_pcle_view", return_value=image), \
             patch.object(scan.time, "sleep"), \
             patch.object(scan, "save_image", side_effect=OSError("disk full")), \
             patch.object(core.MosaicCanvas, "save", side_effect=lambda path: events.append(("save", path))):
            with self.assertRaisesRegex(OSError, "disk full"):
                scan.run_scan()
            self.assertEqual(move.call_count, 2, "failure should not append an automatic home move")
            self.assertEqual(events[0], ("shutdown", "fake-handle"))
            self.assertEqual(events[1][0], "save")
            report = json.loads((Path(temporary) / "trajectory.json").read_text(encoding="utf-8"))
            self.assertEqual(report["metadata"]["mode"], "direct")


if __name__ == "__main__":
    unittest.main()

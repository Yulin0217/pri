"""Client regressions exercised with local sockets and no vendor SDK."""

import builtins
from contextlib import ExitStack
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from smarpod_pcle.apps import client, demo
from smarpod_pcle.net import recv_message, send_message


class ClientTests(unittest.TestCase):
    def test_reply_rejects_nonfinite_or_ambiguous_corrections(self):
        for reply in (
            {"distance": float("nan"), "angle": 0, "axis": 0},
            {"distance": 0, "angle": float("inf"), "axis": 0},
            {"distance": 10, "angle": 2, "axis": 45},
        ):
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                client.Correction.from_reply(reply)

    def test_distance_conversion_and_clear_signal(self):
        position, rotation = [0.0] * 3, [0.0] * 3
        convert = Mock()
        self.assertFalse(client.apply_correction(
            position, rotation, client.Correction(20, 0, 0), convert,
        ))
        self.assertAlmostEqual(position[2], 20e-6)
        self.assertTrue(client.apply_correction(
            position, rotation, client.Correction(0, 0, 45), convert,
        ))
        convert.assert_not_called()

    def test_legacy_angle_rule_preserved(self):
        self.assertEqual(client.legacy_rotation_update(-4, 1), -3)
        self.assertEqual(client.legacy_rotation_update(4, 1), 3)
        self.assertEqual(client.legacy_rotation_update(0, 0, lambda: 0.25), 0.5)

    def test_disconnect_stops_workers(self):
        local, remote = socket.socketpair()
        local.settimeout(1)
        stream = client.FrameStream(local)
        try:
            with patch.object(client, "capture_pcle_view", return_value=b"frame"), \
                 patch.object(client, "encode_frame", side_effect=lambda frame, signal: {
                     "image": frame, "signal": signal,
                 }):
                stream.start()
                self.assertEqual(recv_message(remote)["signal"], 1)
                send_message(remote, {"distance": 2, "angle": 0, "axis": 0})
                self.assertEqual(stream.replies.get(timeout=1), client.Correction(2, 0, 0))
                remote.close()
                self.assertTrue(stream.stopped.wait(1))
                with self.assertRaises(RuntimeError):
                    stream.check_error()
                stream.close()
                self.assertTrue(all(not worker.is_alive() for worker in stream.threads))
        finally:
            stream.close()
            remote.close()

    def test_close_wakes_blocked_receiver(self):
        local, remote = socket.socketpair()
        stream = client.FrameStream(local)
        try:
            with patch.object(client, "capture_pcle_view", return_value=None), \
                 patch.object(client, "encode_frame", return_value={"signal": 1}):
                stream.start()
                recv_message(remote)
                closer = threading.Thread(target=stream.close, daemon=True)
                closer.start()
                closer.join(timeout=2)
                self.assertFalse(closer.is_alive(), "shutdown remained blocked in recv")
        finally:
            remote.close()
            stream.close()

    def test_stream_only_receiver_allows_silent_peer(self):
        local, remote = socket.socketpair()
        local.settimeout(0.01)
        stream = client.FrameStream(local, stream_only=True)
        receiver = threading.Thread(target=stream._worker, args=(stream._receive,))
        stream.threads.append(receiver)
        try:
            receiver.start()
            self.assertFalse(stream.stopped.wait(0.08), "silent server triggered a reply timeout")
            self.assertTrue(receiver.is_alive())
            stream.close()
            self.assertFalse(receiver.is_alive())
            stream.check_error()
        finally:
            remote.close()
            stream.close()

    def test_stream_only_incomplete_reply_still_times_out(self):
        local, remote = socket.socketpair()
        local.settimeout(0.02)
        stream = client.FrameStream(local, stream_only=True)
        receiver = threading.Thread(target=stream._worker, args=(stream._receive,))
        stream.threads.append(receiver)
        try:
            receiver.start()
            remote.sendall(b"\x00\x00")  # Only half of the length header.
            self.assertTrue(stream.stopped.wait(1))
            with self.assertRaises(RuntimeError):
                stream.check_error()
        finally:
            stream.close()
            remote.close()

    def test_stream_only_never_imports_hardware(self):
        real_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.startswith("smaract") or name == "smarpod_pcle.hardware":
                self.fail(f"stream-only mode imported hardware: {name}")
            return real_import(name, *args, **kwargs)

        stream = Mock()
        stream.stopped.wait.return_value = True
        with patch("builtins.__import__", side_effect=guarded_import), \
             patch.object(client.socket, "create_connection"), \
             patch.object(client, "FrameStream", return_value=stream) as stream_class, \
             patch.object(client.threading, "Thread"):
            client.main("2")
        self.assertTrue(stream_class.call_args.kwargs["stream_only"])
        stream.start.assert_called_once()
        stream.close.assert_called_once()

    def _servo_context(self, stack):
        """Provide fake hardware at the vendor boundary; no SDK is imported."""
        temporary = stack.enter_context(tempfile.TemporaryDirectory())
        run_dir = Path(temporary) / "run"
        run_dir.mkdir()
        stack.enter_context(patch.object(client, "create_run_dir", return_value=run_dir))
        stack.enter_context(patch.object(client.threading, "Thread"))
        stack.enter_context(patch.object(client, "capture_mosaic_view", return_value=None))
        stack.enter_context(patch.object(client.cv2, "imwrite", return_value=True))
        stack.enter_context(patch.object(client.time, "sleep"))
        sdk = Mock()
        sdk.Pose.side_effect = lambda *values: tuple(values)
        stack.enter_context(patch("smarpod_pcle.hardware.get_sdk", return_value=sdk))
        initialize = stack.enter_context(patch("smarpod_pcle.hardware.SmarPod_init", return_value="handle"))
        move = stack.enter_context(patch("smarpod_pcle.hardware.move_checked"))
        shutdown = stack.enter_context(patch("smarpod_pcle.hardware.shutdown"))
        stream = Mock()
        stream.stopped = threading.Event()
        stream.replies = client.queue.Queue()
        return sdk, initialize, move, shutdown, stream

    def test_failed_initialization_closes_stream_without_invalid_handle(self):
        with ExitStack() as stack:
            _, initialize, move, shutdown, stream = self._servo_context(stack)
            initialize.side_effect = RuntimeError("referencing failed")
            with self.assertRaisesRegex(RuntimeError, "referencing failed"):
                client._run_servo(stream, "0")
            stream.close.assert_called_once()
            move.assert_not_called()
            shutdown.assert_not_called()

    def test_setup_failure_closes_stream_before_hardware(self):
        with ExitStack() as stack:
            sdk, _, move, shutdown, stream = self._servo_context(stack)
            sdk.SetCoordinateSystem.side_effect = RuntimeError("setup failed")
            cleanup = Mock()
            cleanup.attach_mock(stream.close, "stream_close")
            cleanup.attach_mock(shutdown, "shutdown")
            with self.assertRaisesRegex(RuntimeError, "setup failed"):
                client._run_servo(stream, "0")
            self.assertEqual([call[0] for call in cleanup.mock_calls], ["stream_close", "shutdown"])
            move.assert_not_called()
            shutdown.assert_called_once_with("handle")

    def test_mosaic_completes_then_returns_home(self):
        with ExitStack() as stack:
            _, _, move, shutdown, stream = self._servo_context(stack)
            stack.enter_context(patch.object(client, "build_mosaic_trajectory", return_value=[(1e-4, 0.0)]))
            # Skip the settling delays without setting the shutdown event.
            stack.enter_context(patch.object(stream.stopped, "wait", return_value=False))
            stream.replies.put(client.Correction(0, 0, 0))
            stream.replies.put(client.Correction(0, 0, 0))
            client._run_servo(stream, "0")
            self.assertEqual(move.call_args.args[1], (0.0,) * 6)
            self.assertEqual(move.call_count, 5)
            shutdown.assert_called_once_with("handle")
            stream.close.assert_called_once()

    def test_servo_stop_does_not_return_home(self):
        with ExitStack() as stack:
            _, _, move, shutdown, stream = self._servo_context(stack)
            stack.enter_context(patch("builtins.input", side_effect=["0", "0", "20"]))

            def stop_after_move(timeout):
                stream.stopped.set()
                return True

            stack.enter_context(patch.object(stream.stopped, "wait", side_effect=stop_after_move))
            stream.replies.put(client.Correction(5, 0, 0))
            client._run_servo(stream, "1")
            self.assertEqual(move.call_count, 3)
            self.assertAlmostEqual(move.call_args.args[1][2], -15e-6)
            shutdown.assert_called_once_with("handle")
            stream.close.assert_called_once()

    def test_demo_communication_failure_stops_without_homing(self):
        with ExitStack() as stack:
            _, _, move, shutdown, _ = self._servo_context(stack)
            temporary = stack.enter_context(tempfile.TemporaryDirectory())
            stack.enter_context(patch.object(demo, "create_run_dir", return_value=Path(temporary)))
            connection = stack.enter_context(patch.object(demo.socket, "create_connection"))
            stack.enter_context(patch.object(demo, "build_mosaic_trajectory", return_value=[(1e-4, 0.0)]))
            stack.enter_context(patch.object(demo, "capture_pcle_view", return_value=None))
            stack.enter_context(patch.object(demo, "capture_mosaic_view", return_value=None))
            stack.enter_context(patch.object(demo, "send_frame_and_recv", side_effect=ConnectionError("disconnected")))
            stack.enter_context(patch("builtins.input", return_value=""))
            with self.assertRaisesRegex(ConnectionError, "disconnected"):
                demo.main()
            self.assertEqual(move.call_count, 2)
            self.assertEqual(move.call_args.args[1][0], 1e-4)
            shutdown.assert_called_once_with("handle")
            connection.return_value.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()

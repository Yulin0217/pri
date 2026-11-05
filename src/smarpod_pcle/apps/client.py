"""Visual servoing client with one owner for hardware and interruptible I/O.

Mode 2 streams images without importing the vendor SDK. Modes 0 and 1 retain
the original experimental angle-correction rule, including its random reset.
The server must return either a distance correction, an angle correction, or
zero distance and angle; simultaneous nonzero corrections are rejected.
"""

from dataclasses import dataclass
import json
import math
import queue
import random
import select
import socket
import threading
import time

import cv2
import numpy as np

from smarpod_pcle.capture import capture_mosaic_view, capture_pcle_view
from smarpod_pcle.config import get_settings
from smarpod_pcle.net import encode_frame, recv_message, send_message
from smarpod_pcle.output import create_run_dir


@dataclass(frozen=True)
class Correction:
    distance: float
    angle: float
    axis: float

    @classmethod
    def from_reply(cls, reply):
        if not isinstance(reply, dict):
            raise ValueError("server reply must be a dictionary")
        values = tuple(float(reply[key]) for key in ("distance", "angle", "axis"))
        if not all(math.isfinite(value) for value in values):
            raise ValueError("server corrections must be finite")
        if values[0] != 0 and values[1] != 0:
            raise ValueError("server returned simultaneous distance and angle corrections")
        return cls(*values)


class FrameStream:
    """Keep streaming frames while main-thread motion waits for corrections.

    A signal of 1 requests the next correction; intervening frames have signal
    0. Stream-only mode sends signal 1 continuously and drains replies when
    present; a send-only server may remain silent. Incomplete replies still
    time out so a damaged stream cannot be mistaken for a fresh message.
    """

    def __init__(self, sock, *, stream_only=False):
        self.sock = sock
        self.stream_only = stream_only
        self.stopped = threading.Event()
        self.replies = queue.Queue(maxsize=64)
        self.errors = queue.Queue()
        self._signal = True
        self._signal_lock = threading.Lock()
        self.threads = []

    def request_correction(self):
        with self._signal_lock:
            self._signal = True

    def _next_signal(self):
        with self._signal_lock:
            signal = int(self.stream_only or self._signal)
            self._signal = False
            return signal

    def _worker(self, action):
        try:
            action()
        except Exception as exc:
            if not self.stopped.is_set():
                self.errors.put(exc)
                self.stopped.set()

    def _send(self):
        while not self.stopped.is_set():
            message = encode_frame(capture_pcle_view(), signal=self._next_signal())
            send_message(self.sock, message)
            self.stopped.wait(0.05)

    def _receive(self):
        while not self.stopped.is_set():
            if self.stream_only:
                # A stream-only server need not reply. Wait for readiness before
                # applying the socket timeout to an actual incoming message.
                ready, _, _ = select.select([self.sock], [], [], 0.1)
                if not ready:
                    continue
            reply = recv_message(self.sock)
            if self.stream_only:
                continue
            correction = Correction.from_reply(reply)
            while not self.stopped.is_set():
                try:
                    self.replies.put(correction, timeout=0.1)
                    break
                except queue.Full:
                    continue

    def start(self):
        for name, action in (("frame-sender", self._send), ("reply-receiver", self._receive)):
            worker = threading.Thread(target=self._worker, args=(action,), name=name)
            self.threads.append(worker)
            worker.start()

    def check_error(self):
        try:
            error = self.errors.get_nowait()
        except queue.Empty:
            return
        raise RuntimeError(f"frame stream failed: {error}") from error

    def close(self):
        self.stopped.set()
        # Wake recv/send before joining; no worker ever owns the hardware.
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
        for worker in self.threads:
            worker.join()


def keyboard_listener(stopped):
    print("Press q + Enter (or Ctrl-C) to stop.")
    while not stopped.is_set():
        try:
            command = input().strip().lower()
        except (EOFError, OSError):
            stopped.set()
            return
        if command == "q":
            stopped.set()


def build_mosaic_trajectory():
    """Preserve the original visual-servoing XY scan (metres)."""
    steps = np.concatenate((np.arange(0, 5, 0.4), np.arange(5, 8, 0.1)))
    return [(float(i * np.cos(i * np.pi) * 1e-4),
             float(i * np.sin(i * np.pi) * 1e-4)) for i in steps]


def legacy_rotation_update(current, correction, random_value=random.random):
    """Original experimental controller rule; this is not a calibrated PID.

    A correction whose magnitude reaches the current rotation resets that axis
    to a random positive angle in [0, 2). Smaller corrections move it toward
    zero according to the original sign rule.
    """
    if abs(correction) >= abs(current):
        return 2 * random_value()
    if np.sign(correction) != np.sign(current):
        return current + correction
    return current - correction


def apply_correction(position, rotation, correction, angle_converter):
    """Update the commanded pose and return whether the server reports clear."""
    if correction.distance != 0:
        position[2] += correction.distance * 1e-6
        return False
    if correction.angle != 0:
        angle = max(-10.0, min(10.0, correction.angle))
        increments = angle_converter(angle=angle, axis=correction.axis)
        for axis in (0, 1):
            rotation[axis] = legacy_rotation_update(rotation[axis], increments[axis])
        return False
    return True


def _save_state(out_dir, records, position, rotation, axis=None):
    entry = {
        "timestamp": time.time(),
        "position": dict(zip(("x", "y", "z"), position)),
        "rotation": dict(zip(("rx", "ry", "rz"), rotation)),
    }
    if axis is not None:
        entry["rotation"]["axis"] = axis
    records[len(records)] = entry
    with (out_dir / "state.json").open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=4)


def _prompt_number(prompt, minimum, maximum):
    value = float(input(prompt))
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"value must be between {minimum} and {maximum}")
    return value


def _run_servo(stream, mode):
    # Loading this module or choosing stream-only mode never requires SmarAct.
    from smarpod_pcle.hardware import (
        SmarPod_init, compute_dRx_dRy, get_sdk, move_checked, shutdown,
    )

    smarpod = get_sdk()
    Pose = smarpod.Pose
    settings = get_settings()
    position, rotation = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    if mode == "1":
        axis = _prompt_number("Rotation axis [0, 180] degrees: ", 0, 180)
        angle = _prompt_number("Tilt [-10, 10] degrees: ", -10, 10)
        distance = _prompt_number("Defocus [0, 200] micrometres: ", 0, 200)
        rotation[:2] = compute_dRx_dRy(angle=angle, axis=axis)
        position[2] = -distance * 1e-6

    out_dir = create_run_dir("robot_state")
    (out_dir / "images").mkdir()
    records = {}
    trajectory = build_mosaic_trajectory() if mode == "0" else []
    waypoint = 0
    h = None
    completed = False
    try:
        h = SmarPod_init()
        home = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        smarpod.SetCoordinateSystem(h, home)
        smarpod.SetPivot(h, [0.0, 0.0, settings.robot.probe_tip_z_m])
        move_checked(h, home)
        if mode == "1":
            move_checked(h, Pose(*position, *rotation))
            time.sleep(1)
        _save_state(out_dir, records, position, rotation)
        stream.start()
        threading.Thread(target=keyboard_listener, args=(stream.stopped,), daemon=True).start()
        while not stream.stopped.is_set():
            try:
                correction = stream.replies.get(timeout=0.1)
            except queue.Empty:
                continue
            if stream.stopped.is_set():
                break
            clear = apply_correction(position, rotation, correction, compute_dRx_dRy)
            move_checked(h, Pose(*position, *rotation))
            _save_state(out_dir, records, position, rotation, correction.axis)
            image_path = out_dir / "images" / f"img_{len(records):04d}.png"
            if not cv2.imwrite(str(image_path), capture_mosaic_view()):
                raise OSError(f"could not write {image_path}")
            if stream.stopped.wait(0.5):
                break
            if mode == "0" and clear:
                if waypoint >= len(trajectory):
                    completed = True
                    break
                position[:2] = trajectory[waypoint]
                move_checked(h, Pose(*position, *rotation))
                waypoint += 1
                if stream.stopped.wait(0.5):
                    break
            stream.request_correction()
        stream.check_error()
    finally:
        # Close I/O before returning home or releasing the controller.
        try:
            stream.close()
        finally:
            if h is not None:
                try:
                    if completed:
                        move_checked(h, Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
                finally:
                    shutdown(h)
        print(f"State and captured images: {out_dir}")


def main(mode=None):
    if mode is None:
        mode = input("Mode: 0 = servo + mosaic, 1 = servo, 2 = stream only: ").strip()
    mode = str(mode)
    if mode not in {"0", "1", "2"}:
        raise ValueError("mode must be 0, 1, or 2")
    settings = get_settings()
    # Fail connection setup before touching hardware.
    sock = socket.create_connection(
        (settings.server.host, settings.server.port), timeout=settings.server.timeout_s,
    )
    stream = FrameStream(sock, stream_only=mode == "2")
    try:
        if mode == "2":
            stream.start()
            threading.Thread(target=keyboard_listener, args=(stream.stopped,), daemon=True).start()
            while not stream.stopped.wait(0.1):
                pass
            stream.check_error()
        else:
            _run_servo(stream, mode)
    except KeyboardInterrupt:
        print("Interrupted; stopping without an automatic home move.")
    finally:
        stream.close()


if __name__ == "__main__":
    main()

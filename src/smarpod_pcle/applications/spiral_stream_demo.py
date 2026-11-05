"""Local spiral scan; server replies are drained but never drive motion."""

import socket
import time

import cv2
import numpy as np

from smarpod_pcle.screen_capture import capture_mosaic_view, capture_pcle_view
from smarpod_pcle.config import get_settings
from smarpod_pcle.tcp_protocol import encode_frame, recv_message, send_message
from smarpod_pcle.run_output import create_run_dir


def build_mosaic_trajectory():
    """Preserve the original demonstration scan in metres."""
    steps = np.concatenate((np.arange(0, 5, 0.3), np.arange(5, 8, 0.08)))
    return [(float(i * np.cos(i * np.pi * 1.12) * 1e-4),
             float(i * np.sin(i * np.pi * 1.12) * 1e-4)) for i in steps]


def send_frame_and_recv(sock, image, signal=1):
    """Complete one frame/reply exchange; the reply is not a motion command."""
    send_message(sock, encode_frame(image, signal=signal))
    return recv_message(sock)


def main():
    from smarpod_pcle.robot_control import SmarPod_init, get_sdk, move_checked, shutdown

    smarpod = get_sdk()
    Pose = smarpod.Pose
    settings = get_settings()
    out_dir = create_run_dir("mosaic_demo")
    images = out_dir / "images"
    images.mkdir()
    h = None
    try:
        # Verify network availability before calibration/referencing can move.
        with socket.create_connection(
            (settings.server.host, settings.server.port), timeout=settings.server.timeout_s,
        ) as sock:
            h = SmarPod_init()
            home = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            smarpod.SetCoordinateSystem(h, home)
            smarpod.SetPivot(h, [0.0, 0.0, settings.robot.probe_tip_z_m])
            move_checked(h, home)
            trajectory = build_mosaic_trajectory()
            print(f"Mosaic trajectory length: {len(trajectory)}")
            input("Press Enter to start; scan begins after a 5 s delay: ")
            time.sleep(5)
            for index, (x, y) in enumerate(trajectory):
                # The local trajectory is the sole source of position commands.
                move_checked(h, Pose(x, y, 0.0, 0.0, 0.0, 0.0))
                time.sleep(0.5)
                frame = capture_pcle_view()
                for name, image in (("img", capture_mosaic_view()), ("frame", frame)):
                    path = images / f"{name}_{index:04d}.png"
                    if not cv2.imwrite(str(path), image):
                        raise OSError(f"could not write {path}")
                reply = send_frame_and_recv(sock, frame)
                print(f"[{index:04d}] received {type(reply).__name__}; reply ignored for motion.")
            move_checked(h, home)
    except KeyboardInterrupt:
        print("Interrupted; stopping without an automatic home move.")
    finally:
        # The socket context exits first; stop/close the stage even if capture,
        # image persistence, or the frame/reply exchange failed partway through.
        if h is not None:
            shutdown(h)
    print(f"Images saved in: {out_dir}")


if __name__ == "__main__":
    main()

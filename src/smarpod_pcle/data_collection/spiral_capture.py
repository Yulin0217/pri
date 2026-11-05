"""Slow XY spiral collection with measured poses and optional inference logging.

Server replies are recorded but never used for motion. The historical
summer-school experiment uses 25 micrometres/second and saves both the probe
view and mosaic view; it does not stitch frames itself.
"""

import socket
import time

import numpy as np

from smarpod_pcle.config import get_settings

USE_SERVER = False
SETTLE_S = 0.5
SPEED_M_S = 2.5e-5
START_DELAY_S = 5.0
PIVOT_XYZ = None


def build_mosaic_trajectory(
    spiral_wind=1.12,
    step_a=(0.0, 5.0, 0.3),
    step_b=(5.0, 8.0, 0.08),
    scale=1e-4,
):
    """Return the original experiment's XY waypoints, in metres.

    These points control the stage directly; optional inference replies are
    measurements for the log and cannot modify this trajectory.
    """
    steps = np.concatenate((np.arange(*step_a), np.arange(*step_b)))
    return [
        (
            float(i * np.cos(i * np.pi * spiral_wind) * scale),
            float(i * np.sin(i * np.pi * spiral_wind) * scale),
        )
        for i in steps
    ]


def try_connect_server():
    """Return a socket with bounded I/O, or None for an offline scan."""
    if not USE_SERVER:
        print("Running the open-loop spiral without a server.")
        return None
    server = get_settings().server
    try:
        sock = socket.create_connection((server.host, server.port), timeout=server.timeout_s)
        print(f"Connected to server: {server.host}:{server.port}")
        return sock
    except OSError as error:
        print(f"Server unavailable ({error}); continuing without inference logging.")
        return None


def main():
    import cv2
    import smaract.smarpod as smarpod
    from smaract.smarpod import Pose

    from smarpod_pcle.screen_capture import capture_mosaic_view, capture_pcle_view
    from smarpod_pcle.robot_control import SmarPod_init, move_checked, pose_to_str, shutdown
    from smarpod_pcle.tcp_protocol import encode_frame, recv_message, send_message
    from smarpod_pcle.run_output import create_run_dir

    out_dir = create_run_dir("mosaic_demo")
    images_dir = out_dir / "images"
    images_dir.mkdir()
    positions_path = out_dir / "positions.txt"
    h = None
    sock = None
    home = Pose(0, 0, 0, 0, 0, 0)
    try:
        h = SmarPod_init()
        smarpod.SetSpeed(h, 1, SPEED_M_S)
        smarpod.SetCoordinateSystem(h, home)
        if PIVOT_XYZ is not None:
            smarpod.SetPivot(h, PIVOT_XYZ)
        move_checked(h, home)
        time.sleep(SETTLE_S)
        trajectory = build_mosaic_trajectory()
        print(f"Trajectory: {len(trajectory)} waypoints at {SPEED_M_S:g} m/s")
        sock = try_connect_server()
        with positions_path.open("w", encoding="utf-8") as log:
            log.write(
                "# step\tt_elapsed_s\t"
                "cmd_x\tcmd_y\tcmd_z\tcmd_rx\tcmd_ry\tcmd_rz\t"
                "meas_x\tmeas_y\tmeas_z\tmeas_rx\tmeas_ry\tmeas_rz\t"
                "server_distance\tserver_angle\tserver_axis\tframe_jpg\tmosaic_jpg\n"
            )
            input("Press Enter to start the spiral after a 5 second delay... ")
            time.sleep(START_DELAY_S)
            started = time.monotonic()
            for idx, (x, y) in enumerate(trajectory):
                pose = Pose(x, y, 0, 0, 0, 0)
                if not smarpod.IsPoseReachable(h, pose):
                    print(f"[{idx:04d}] Skipping unreachable pose {pose_to_str(pose)}")
                    continue
                move_checked(h, pose)
                time.sleep(SETTLE_S)
                measured = smarpod.GetPose(h)
                elapsed = time.monotonic() - started
                frame = capture_pcle_view()
                mosaic = capture_mosaic_view()
                frame_name = f"frame_{idx:04d}.jpg"
                mosaic_name = f"img_{idx:04d}.jpg"
                # Write both images before adding a row that refers to their filenames.
                for filename, image in ((frame_name, frame), (mosaic_name, mosaic)):
                    if not cv2.imwrite(str(images_dir / filename), image):
                        raise OSError(f"Could not save {filename}")
                distance = angle = axis = float("nan")
                if sock is not None:
                    try:
                        send_message(sock, encode_frame(frame, signal=1))
                        reply = recv_message(sock)
                        distance = float(reply.get("distance", float("nan")))
                        angle = float(reply.get("angle", float("nan")))
                        axis = float(reply.get("axis", float("nan")))
                    except Exception as error:
                        print(f"[{idx:04d}] Inference logging failed: {error}; continuing offline.")
                        sock.close()
                        sock = None
                log.write(
                    f"{idx}\t{elapsed:.6f}\t{x:.10e}\t{y:.10e}\t0\t0\t0\t0\t"
                    f"{measured.positionX:.10e}\t{measured.positionY:.10e}\t"
                    f"{measured.positionZ:.10e}\t{measured.rotationX:.10e}\t"
                    f"{measured.rotationY:.10e}\t{measured.rotationZ:.10e}\t"
                    f"{distance}\t{angle}\t{axis}\t{frame_name}\t{mosaic_name}\n"
                )
                log.flush()
                print(f"[{idx:04d}] Saved frame at x={x:+.4e}, y={y:+.4e}")
        move_checked(h, home)
    except KeyboardInterrupt:
        print("\nInterrupted; retaining completed frames and log rows.")
    finally:
        try:
            if sock is not None:
                sock.close()
        finally:
            # The home move above is for a completed scan; errors stop at the current pose.
            shutdown(h)
    print(f"Saved images and positions.txt to {out_dir}")


if __name__ == "__main__":
    main()

"""
Spiral mosaic data collection for the SmarPod + optional remote server.

What this script does
---------------------
1. Builds an open-loop spiral trajectory in the XY plane.
2. Moves the SmarPod to each waypoint (this does NOT require the server).
3. Captures two screen regions (small probe frame + larger mosaic view).
4. Optionally sends the small frame to the AGX/server (same pickle protocol
   as client.py) when USE_SERVER is True and the host is reachable.
5. Saves JPGs and a positions log under one output folder. Server replies are
   read (to keep the socket healthy) but are NOT used to drive motion — the
   spiral alone decides XY.

Run
---
    python summer_school/data_collection.py

Before running, set HOST / PORT if you need the server, and ensure the probe
has clear space to move over the spiral range.
"""

import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pickle
import socket
import struct

# Make the repo root importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import smaract.smarpod as smarpod
from smaract.smarpod import Pose

from common.capture import capture_partial_screen
from common.utils_client import SmarPod_init, pose_to_str

# ---------------------------------------------------------------------------
# Network: optional; motion runs even when the server is down
# ---------------------------------------------------------------------------
USE_SERVER = False
HOST = "172.30.28.159"
PORT = 12334
CONNECT_TIMEOUT_S = 5.0

# ---------------------------------------------------------------------------
# Screen capture regions (pixels). Tune these to your display layout.
# ---------------------------------------------------------------------------
# Small crop sent to the server (probe FOV).
FRAME_REGION = dict(top=45, left=1118, width=350, height=350)
# Larger crop saved locally for mosaic inspection.
MOSAIC_REGION = dict(top=420, left=1050, width=600, height=600)

# Settling time after each Move before grabbing images (seconds).
SETTLE_S = 0.5

# Stage speed (m/s). SmarPod_init defaults to 3e-3 (3 mm/s); 1e-3 is 1/3 of that.
SPEED_M_S = 2.5e-5

# Delay after the user presses Enter, before the scan starts (seconds).
START_DELAY_S = 5.0

# Pivot: tip offset from the SmarPod's default pivot (metres).
# mosaic_direct.py leaves the default pivot; for pure XY spiral motion either
# works. Set to None to skip SetPivot (same as mosaic_direct).
PIVOT_XYZ = None  # e.g. [0.0, 0.0, 37.4e-3] if you need tip-pivot later


# ---------------------------------------------------------------------------
# Image capture
# ---------------------------------------------------------------------------

def capture_probe_frame():
    """Capture the small probe FOV that is sent to the server."""
    return capture_partial_screen(**FRAME_REGION, gray=True)


def capture_mosaic_view():
    """Capture the larger on-screen mosaic view saved for inspection."""
    return capture_partial_screen(**MOSAIC_REGION, gray=True)


# ---------------------------------------------------------------------------
# Socket protocol (length-prefixed pickle, same as client.py)
# ---------------------------------------------------------------------------

def recv_exact(sock, size):
    """Receive exactly `size` bytes, or raise if the peer disconnects."""
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            raise ConnectionError("server disconnected while receiving data")
        data += packet
    return data


def send_frame_and_recv(sock, image, signal=1):
    """
    Resize `image` to 224x224 JPEG, send it with a signal flag, and return
    the server's pickled reply.

    Wire format:
        [4-byte big-endian length][pickle({"image": jpeg_bytes, "signal": int})]
    Reply uses the same length-prefix framing.
    """
    image_224 = cv2.resize(image, (224, 224), interpolation=cv2.INTER_CUBIC)
    ok, img_encoded = cv2.imencode(".jpg", image_224)
    if not ok:
        raise RuntimeError("failed to encode image")

    payload = pickle.dumps({"image": img_encoded.tobytes(), "signal": signal})
    sock.sendall(struct.pack("!I", len(payload)) + payload)

    data_len = struct.unpack("!I", recv_exact(sock, 4))[0]
    data = recv_exact(sock, data_len)
    return pickle.loads(data)


def try_connect_server():
    """Return a connected socket, or None if USE_SERVER is False / connect fails."""
    if not USE_SERVER:
        print("USE_SERVER=False; running open-loop spiral without network.")
        return None
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(CONNECT_TIMEOUT_S)
    try:
        sock.connect((HOST, PORT))
        sock.settimeout(None)
        print(f"connected to server: {HOST}:{PORT}")
        return sock
    except OSError as exc:
        sock.close()
        print(f"server unavailable ({HOST}:{PORT}): {exc}")
        print("continuing open-loop spiral without network.")
        return None


# ---------------------------------------------------------------------------
# Trajectory: open-loop Archimedean-style spiral in XY
# ---------------------------------------------------------------------------

def build_mosaic_trajectory(
    spiral_wind=1.12,
    step_a=(0.0, 5.0, 0.3),
    step_b=(5.0, 8.0, 0.08),
    scale=1e-4,
):
    """
    Build a list of (x, y) waypoints along a planar spiral (metres).

    Pure XY translation only — no Z motion and no tip tilt.
    """
    steps = np.concatenate(
        (np.arange(*step_a), np.arange(*step_b))
    )

    trajectory = []
    for i in steps:
        ang = i * np.pi * spiral_wind
        x = i * np.cos(ang) * scale
        y = i * np.sin(ang) * scale
        trajectory.append((float(x), float(y)))
    return trajectory


def safe_shutdown(h, p_home):
    if h is None:
        return
    try:
        smarpod.Move(h, p_home, 0, True)
        print("final pose:", pose_to_str(smarpod.GetPose(h)))
        smarpod.Stop(h)
    finally:
        smarpod.Close(h)
        print("device closed")


# ---------------------------------------------------------------------------
# Main scan loop
# ---------------------------------------------------------------------------

def main():
    # Output folder layout:
    #   mosaic_demo_<timestamp>/
    #     images/frame_XXXX.jpg   — probe FOV
    #     images/img_XXXX.jpg     — mosaic view
    #     positions.txt           — timestep + poses + server commands
    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = f"mosaic_demo_{current_time}"
    images_dir = os.path.join(out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    positions_path = os.path.join(out_dir, "positions.txt")

    h = None
    sock = None
    p_home = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    try:
        # --- SmarPod setup (same pattern as mosaic_direct.py) ----------------
        h = SmarPod_init()
        smarpod.SetSpeed(h, 1, SPEED_M_S)
        print("speed set to %.3e m/s (%.2f mm/s)" % (SPEED_M_S, SPEED_M_S * 1e3))
        csys = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        smarpod.SetCoordinateSystem(h, csys)
        if PIVOT_XYZ is not None:
            smarpod.SetPivot(h, PIVOT_XYZ)
            print("pivot point:", smarpod.GetPivot(h))
        print("coordinate system:", pose_to_str(csys))
        smarpod.Move(h, p_home, 0, True)
        time.sleep(SETTLE_S)

        trajectory = build_mosaic_trajectory()
        print("mosaic trajectory length:", len(trajectory))

        sock = try_connect_server()

        with open(positions_path, "w", encoding="utf-8") as log:
            log.write(
                "# step\tt_elapsed_s\t"
                "cmd_x\tcmd_y\tcmd_z\tcmd_rx\tcmd_ry\tcmd_rz\t"
                "meas_x\tmeas_y\tmeas_z\tmeas_rx\tmeas_ry\tmeas_rz\t"
                "server_distance\tserver_angle\tserver_axis\t"
                "frame_jpg\tmosaic_jpg\n"
            )

            input("Press Enter to start; scan begins after a short delay… ")
            print(f"starting scan in {START_DELAY_S:.0f} s…")
            time.sleep(START_DELAY_S)
            t0 = time.time()

            for idx, (x, y) in enumerate(trajectory):
                cmd_z = cmd_rx = cmd_ry = cmd_rz = 0.0
                p = Pose(x, y, cmd_z, cmd_rx, cmd_ry, cmd_rz)
                if not smarpod.IsPoseReachable(h, p):
                    print(f"[{idx:04d}] skip unreachable pose: {pose_to_str(p)}")
                    continue

                smarpod.Move(h, p, 0, True)
                time.sleep(SETTLE_S)

                measured = smarpod.GetPose(h)
                t_elapsed = time.time() - t0

                frame = capture_probe_frame()
                mosaic_img = capture_mosaic_view()
                frame_name = f"frame_{idx:04d}.jpg"
                mosaic_name = f"img_{idx:04d}.jpg"
                cv2.imwrite(os.path.join(images_dir, frame_name), frame)
                cv2.imwrite(os.path.join(images_dir, mosaic_name), mosaic_img)

                server_distance = server_angle = server_axis = float("nan")
                if sock is not None:
                    try:
                        server_reply = send_frame_and_recv(sock, frame, signal=1)
                        server_distance = float(server_reply.get("distance", float("nan")))
                        server_angle = float(server_reply.get("angle", float("nan")))
                        server_axis = float(server_reply.get("axis", float("nan")))
                        print(
                            f"[{idx:04d}] t={t_elapsed:.3f}s  "
                            f"cmd=({x:.6e}, {y:.6e})  "
                            f"server dist/angle/axis="
                            f"{server_distance}/{server_angle}/{server_axis}  "
                            "(ignored for motion)"
                        )
                    except Exception as exc:
                        print(f"[{idx:04d}] communication failed: {exc}")
                        print("continuing motion without server.")
                        try:
                            sock.close()
                        except Exception:
                            pass
                        sock = None
                else:
                    print(
                        f"[{idx:04d}] t={t_elapsed:.3f}s  "
                        f"cmd=({x:.6e}, {y:.6e})  meas=({measured.positionX:.6e}, "
                        f"{measured.positionY:.6e})"
                    )

                log.write(
                    f"{idx}\t{t_elapsed:.6f}\t"
                    f"{x:.10e}\t{y:.10e}\t{cmd_z:.10e}\t"
                    f"{cmd_rx:.10e}\t{cmd_ry:.10e}\t{cmd_rz:.10e}\t"
                    f"{measured.positionX:.10e}\t{measured.positionY:.10e}\t"
                    f"{measured.positionZ:.10e}\t"
                    f"{measured.rotationX:.10e}\t{measured.rotationY:.10e}\t"
                    f"{measured.rotationZ:.10e}\t"
                    f"{server_distance}\t{server_angle}\t{server_axis}\t"
                    f"{frame_name}\t{mosaic_name}\n"
                )
                log.flush()

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        safe_shutdown(h, p_home)
        print(f"done. saved under: {out_dir}")
        print(f"  images:    {images_dir}")
        print(f"  positions: {positions_path}")


if __name__ == "__main__":
    main()

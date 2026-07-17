"""Regression-based mosaicking (over TCP/IP).

Scans the probe over a local spiral trajectory. For every waypoint the captured
pCLE frame is sent to a regression server, which returns the frame's estimated
displacement relative to the previous frame. Those displacements are accumulated
to position each frame on the mosaic canvas, so the stitching geometry comes from
the learned regression model rather than the commanded stage pose. If the server
is unreachable or returns an invalid reply, the placement falls back to the
commanded pose so the scan still produces a mosaic.

Protocol (length-prefixed pickle, matching apps/client.py wire format):
    client -> server: {'image': <jpeg bytes, 224x224 grayscale>, 'signal': 1}
    server -> client: {'dx': float, 'dy': float}   # displacement from the
                                                    # previous frame, in pixels
Set REGRESSION_IN_MICROMETERS = True if your server returns micrometres instead.

Run:
    python mosaicking/mosaic_regression.py
"""

import json
import os
import socket
import sys
import time
from pathlib import Path

import cv2

# Make the repo root importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import smaract.smarpod as smarpod
from smaract.smarpod import Pose

from common.capture import capture_pcle_view
from common.net import send_message, recv_message
from common.utils_client import SmarPod_init, pose_to_str
from mosaicking.mosaic_core import (
    build_spiral_trajectory, estimate_canvas_size, MosaicCanvas,
)

# ---- Configuration --------------------------------------------------------
HOST = "172.30.28.159"    # regression server IP
PORT = 12334              # regression server port
METERS_PER_PIXEL = 1e-6   # CALIBRATE: stage travel per mosaic pixel (m/px)
REGRESSION_IN_MICROMETERS = False  # True if server returns dx/dy in micrometres
BLEND = "average"         # "average" | "max" | "overwrite"
SIGN_X = 1                # flip to align stage X with image X (+1 / -1)
SIGN_Y = 1                # flip to align stage Y with image Y (+1 / -1)
SETTLE_S = 0.5            # settle time after each move, before capturing
SAVE_EVERY = 20           # write the current mosaic every N frames (0 disables)
# ---------------------------------------------------------------------------


def query_displacement(sock, frame):
    """Send a frame to the regression server and return (dx_px, dy_px).

    Raises on any communication/format error so the caller can fall back.
    """
    frame_224 = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_CUBIC)
    ok, encoded = cv2.imencode(".jpg", frame_224)
    if not ok:
        raise RuntimeError("failed to encode frame")
    send_message(sock, {"image": encoded.tobytes(), "signal": 1})
    reply = recv_message(sock)
    dx = float(reply["dx"])
    dy = float(reply["dy"])
    if REGRESSION_IN_MICROMETERS:
        dx = dx * 1e-6 / METERS_PER_PIXEL
        dy = dy * 1e-6 / METERS_PER_PIXEL
    return dx, dy


def commanded_delta_px(prev_xy, xy):
    """Pixel displacement implied by the commanded stage move (fallback)."""
    dx_px = SIGN_X * (xy[0] - prev_xy[0]) / METERS_PER_PIXEL
    dy_px = -SIGN_Y * (xy[1] - prev_xy[1]) / METERS_PER_PIXEL
    return dx_px, dy_px


def safe_shutdown(h):
    if h is None:
        return
    try:
        smarpod.Move(h, Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0, True)
        smarpod.Stop(h)
    finally:
        smarpod.Close(h)
        print("device closed")


def main():
    out_dir = time.strftime("mosaic_regression_%Y-%m-%d_%H-%M-%S")
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    mosaic_path = os.path.join(out_dir, "mosaic.png")

    trajectory = build_spiral_trajectory()
    print("trajectory length:", len(trajectory))

    h = None
    canvas = None
    records = {}
    sock = None
    try:
        h = SmarPod_init()
        csys = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        smarpod.SetCoordinateSystem(h, csys)
        smarpod.Move(h, Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0, True)
        time.sleep(SETTLE_S)

        sample = capture_pcle_view(gray=True)
        height, width = estimate_canvas_size(trajectory, METERS_PER_PIXEL, sample.shape)
        canvas = MosaicCanvas(height, width, METERS_PER_PIXEL, BLEND, SIGN_X, SIGN_Y)
        print("mosaic canvas size: %dx%d px (frame %dx%d)" % (width, height, sample.shape[1], sample.shape[0]))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        print("connected to regression server %s:%d" % (HOST, PORT))

        acc_x, acc_y = 0.0, 0.0
        prev_xy = None
        for idx, (x, y) in enumerate(trajectory):
            pose = Pose(x, y, 0.0, 0.0, 0.0, 0.0)
            if not smarpod.IsPoseReachable(h, pose):
                print("skip unreachable pose %d: %s" % (idx, pose_to_str(pose)))
                continue

            smarpod.Move(h, pose, 0, True)
            time.sleep(SETTLE_S)
            frame = capture_pcle_view(gray=True)

            if idx == 0 or prev_xy is None:
                dx_px, dy_px, source = 0.0, 0.0, "reference"
            else:
                try:
                    dx_px, dy_px = query_displacement(sock, frame)
                    source = "regression"
                except Exception as exc:
                    dx_px, dy_px = commanded_delta_px(prev_xy, (x, y))
                    source = "fallback"
                    print("frame %04d: regression failed (%s); using commanded pose" % (idx, exc))

            acc_x += dx_px
            acc_y += dy_px
            canvas.place_center_px(frame, acc_x, acc_y)
            cv2.imwrite(os.path.join(frames_dir, "frame_%04d.png" % idx), frame)
            records[idx] = {
                "x_m": x, "y_m": y,
                "dx_px": dx_px, "dy_px": dy_px,
                "acc_x_px": acc_x, "acc_y_px": acc_y,
                "source": source,
            }
            print("placed frame %04d via %s at px=(%.1f, %.1f)" % (idx, source, acc_x, acc_y))
            prev_xy = (x, y)

            if SAVE_EVERY and (idx + 1) % SAVE_EVERY == 0:
                canvas.save(mosaic_path)

        smarpod.Move(h, Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 0, True)
    except KeyboardInterrupt:
        print("\nInterrupted by user; saving mosaic so far.")
    finally:
        if sock is not None:
            sock.close()
        if canvas is not None:
            canvas.save(mosaic_path)
            print("mosaic saved to %s" % mosaic_path)
        with open(os.path.join(out_dir, "trajectory.json"), "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "mode": "regression",
                    "host": HOST, "port": PORT,
                    "meters_per_pixel": METERS_PER_PIXEL,
                    "regression_in_micrometers": REGRESSION_IN_MICROMETERS,
                    "blend": BLEND,
                    "sign_x": SIGN_X, "sign_y": SIGN_Y,
                },
                "frames": records,
            }, f, indent=4)
        safe_shutdown(h)


if __name__ == "__main__":
    main()

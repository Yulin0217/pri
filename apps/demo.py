import os
import pickle
import socket
import struct
import time
import cv2
import numpy as np
import smaract.smarpod as smarpod
from mss import mss
from smaract.smarpod import Pose as Pose

# Make the repo root importable so `common` resolves when this file is run directly.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.utils_client import SmarPod_init, pose_to_str

HOST = "172.30.28.159"
PORT = 12334


def capture_partial_screen(top, left, width, height):
    with mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}
        img = sct.grab(monitor)
        img_np = np.array(img)
        img_gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
    return img_gray


def capture_image():
    return capture_partial_screen(45, 1118, 350, 350)


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            raise ConnectionError("server disconnected while receiving data")
        data += packet
    return data


def send_frame_and_recv(sock, image, signal=1):
    image_224 = cv2.resize(image, (224, 224), interpolation=cv2.INTER_CUBIC)
    ok, img_encoded = cv2.imencode(".jpg", image_224)
    if not ok:
        raise RuntimeError("failed to encode image")

    payload = pickle.dumps({"image": img_encoded.tobytes(), "signal": signal})
    sock.sendall(struct.pack("!I", len(payload)) + payload)

    data_len = struct.unpack("!I", recv_exact(sock, 4))[0]
    data = recv_exact(sock, data_len)
    return pickle.loads(data)


def build_mosaic_trajectory():
    # >1: more winding per radius (tighter rings); smaller step = denser samples along the path.
    spiral_wind = 1.12
    step_a = np.arange(0, 5, 0.3)
    step_b = np.arange(5, 8, 0.08)
    steps = np.concatenate((step_a, step_b))

    trajectory = []
    for i in steps:
        ang = i * np.pi * spiral_wind
        x = i * np.cos(ang) * 1e-4
        y = i * np.sin(ang) * 1e-4
        trajectory.append([x, y, 0.0, 0.0, 0.0])
    return trajectory


def main():
    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = f"mosaic_demo_{current_time}"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "images"), exist_ok=True)

    h = SmarPod_init()
    p_home = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    csys = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    smarpod.SetCoordinateSystem(h, csys)
    smarpod.SetPivot(h, [0, 0, 37.4e-3])
    print("setting coordinate system to %s" % pose_to_str(csys))
    print("pivot point is %s" % smarpod.GetPivot(h))
    smarpod.Move(h, p_home, 0, True)

    trajectory = build_mosaic_trajectory()
    print("Mosaic trajectory length:", len(trajectory))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"Connected to server: {HOST}:{PORT}")

        input("Press Enter to start; scan begins after a 5 s delay… ")
        print("Starting scan in 5 seconds…")
        time.sleep(5)

        for idx, xyzrr in enumerate(trajectory):
            p = Pose(xyzrr[0], xyzrr[1], xyzrr[2], xyzrr[3], xyzrr[4], 0.0)
            smarpod.Move(h, p, 0, True)
            time.sleep(0.5)

            frame = capture_image()
            mosaic_img = capture_partial_screen(420, 1050, 600, 600)
            cv2.imwrite(os.path.join(out_dir, "images", f"img_{idx:04d}.png"), mosaic_img)
            cv2.imwrite(os.path.join(out_dir, "images", f"frame_{idx:04d}.png"), frame)

            try:
                server_reply = send_frame_and_recv(sock, frame, signal=1)
                # Read reply for flow control only; do not use pose/commands from server for motion.
                print(f"[{idx:04d}] server keys: {list(server_reply.keys())}, ignored for mosaic.")
            except Exception as exc:
                print(f"[{idx:04d}] communication failed: {exc}")
                break

    smarpod.Move(h, p_home, 0, True)
    pose = smarpod.GetPose(h)
    print("final pose = %s" % pose_to_str(pose))
    smarpod.Stop(h)
    smarpod.Close(h)
    print(f"Done. Images saved in: {out_dir}")


if __name__ == "__main__":
    main()
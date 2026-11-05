"""Shared scan lifecycle for direct and regression mosaics."""

import json
import time
from smarpod_pcle.screen_capture import capture_pcle_view
from smarpod_pcle.config import get_settings
from smarpod_pcle.robot_control import SmarPod_init, get_sdk, move_checked, shutdown
from smarpod_pcle.run_output import create_run_dir, save_image
from .mosaic_canvas import MosaicCanvas, build_spiral_trajectory, estimate_canvas_size
from .regression_mosaic import DisplacementSource


def run_scan(*, regression=False):
    """Capture a stage scan and place each frame using physical or inferred offsets."""
    sdk = get_sdk()
    cfg = get_settings().mosaic
    mode = "regression" if regression else "direct"
    out_dir = create_run_dir(f"mosaic_{mode}")
    frames_dir = out_dir / "frames"
    frames_dir.mkdir()
    trajectory = (build_spiral_trajectory() if regression else
                  build_spiral_trajectory(coarse_step=0.2, fine_step=0.065))
    settle = 0.5 if regression else 0.6
    source = DisplacementSource() if regression else None
    handle, canvas = None, None
    records = {}
    try:
        if source is not None:
            source.connect()
        handle = SmarPod_init()
        if not regression:
            sdk.SetSpeed(handle, 1, min(0.002, get_settings().robot.speed_m_s))
        home = sdk.Pose(0., 0., 0., 0., 0., 0.)
        sdk.SetCoordinateSystem(handle, home)
        move_checked(handle, home)
        time.sleep(settle)
        sample = capture_pcle_view()
        height, width = estimate_canvas_size(trajectory, cfg.meters_per_pixel, sample.shape)
        canvas = MosaicCanvas(height, width, cfg.meters_per_pixel, cfg.blend, cfg.sign_x, cfg.sign_y)
        previous = None
        acc_x, acc_y = 0., 0.
        for index, (x, y) in enumerate(trajectory):
            pose = sdk.Pose(x, y, 0., 0., 0., 0.)
            if not sdk.IsPoseReachable(handle, pose):
                print(f"Skipping unreachable waypoint {index}")
                continue
            move_checked(handle, pose)
            time.sleep(settle)
            frame = capture_pcle_view()
            record = {"x_m": x, "y_m": y}
            if source is not None:
                dx, dy, origin = source.offset(frame, previous, (x, y))
                # Both model and fallback offsets are deltas from the last captured frame.
                # Accumulate them in one coordinate system even after model failure.
                acc_x += dx
                acc_y += dy
                placed = canvas.place_center_px(frame, acc_x, acc_y)
                record.update(dx_px=dx, dy_px=dy, acc_x_px=acc_x, acc_y_px=acc_y, source=origin)
            else:
                placed = canvas.place_meters(frame, x, y)
                record["source"] = "commanded"
            record["placed"] = placed
            if not placed:
                print(f"Frame {index} lies outside the mosaic canvas; raw image is still saved.")
            save_image(frames_dir / f"frame_{index:04d}.png", frame)
            # Only saved frames enter the trajectory manifest and next-frame reference.
            records[index] = record
            previous = (x, y)
            if (index + 1) % 20 == 0:
                canvas.save(out_dir / "mosaic.png")
        move_checked(handle, home)
    except KeyboardInterrupt:
        print("Interrupted; saving frames and stopping without an automatic home move.")
    finally:
        # Stop hardware before file I/O; both cleanup and persistence are attempted.
        # Error cleanup adds no home move, which could cross the sample unexpectedly.
        try:
            try:
                shutdown(handle)
            finally:
                if source is not None:
                    source.close()
        finally:
            try:
                with (out_dir / "trajectory.json").open("w", encoding="utf-8") as file:
                    json.dump({"metadata": {"mode": mode, **get_settings().as_dict()},
                               "frames": records}, file, indent=2)
            finally:
                if canvas is not None:
                    canvas.save(out_dir / "mosaic.png")
    print(f"Mosaic and frames: {out_dir}")

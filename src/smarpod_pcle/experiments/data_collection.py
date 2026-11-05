# Copyright (c) 2020 SmarAct GmbH

# Programming example for the SmarPod Python API.

# THIS  SOFTWARE, DOCUMENTS, FILES AND INFORMATION ARE PROVIDED 'AS IS'
# WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING,
# BUT  NOT  LIMITED  TO,  THE  IMPLIED  WARRANTIES  OF MERCHANTABILITY,
# FITNESS FOR A PURPOSE, OR THE WARRANTY OF NON-INFRINGEMENT.
# THE  ENTIRE  RISK  ARISING OUT OF USE OR PERFORMANCE OF THIS SOFTWARE
# REMAINS WITH YOU.
# IN  NO  EVENT  SHALL  THE  SMARACT  GMBH  BE  LIABLE  FOR ANY DIRECT,
# INDIRECT, SPECIAL, INCIDENTAL, CONSEQUENTIAL OR OTHER DAMAGES ARISING
# OUT OF THE USE OR INABILITY TO USE THIS SOFTWARE.
#
# WHEN RUNNING, THIS PROGRAMMING EXAMPLE WILL MOVE THE POSITIONER.
# ENSURE THAT THIS CAN'T CAUSE COLLISIONS. THE POSITIONER MUST HAVE
# SUFFICIENT SPACE TO MOVE OVER ITS FULL RANGE.


"""Historical XY image grid with 41 repeated frames at each XY location.

The suffix 0, 10, ..., 400 in each image filename is a legacy sample label,
NOT a Z displacement: the original experiment disabled its Z sweep. Use the
distance collector to obtain actual defocus labels.
"""

import json


def grid_samples():
    """Yield legacy filename indices and physical XYZ targets (metres)."""
    for i in range(-10, 11):
        for j in range(-10, 11):
            for sample_label in range(0, 401, 10):
                yield i, j, sample_label, (i * 1e-4, j * 1e-4, 0.0)


def main():
    import cv2
    import smaract.smarpod as smarpod
    from smaract.smarpod import Pose

    from smarpod_pcle.capture import capture_pcle_view
    from smarpod_pcle.hardware import SmarPod_init, move_checked, pose_to_str, shutdown
    from smarpod_pcle.output import create_run_dir

    print("Legacy grid: 21 x 21 XY locations, 41 repeated frames each, Z = 0.")
    save_root = input("Output directory (Enter for configured output directory): ").strip()
    out_dir = create_run_dir("clear_blur_data", root=save_root or None)
    records = {}
    h = None
    try:
        h = SmarPod_init()
        smarpod.SetPivot(h, [0, 0, 0])
        home = Pose(0, 0, 0, 0, 0, 0)
        smarpod.SetCoordinateSystem(h, home)
        for idx, (i, j, sample_label, xyz) in enumerate(grid_samples()):
            pose = Pose(*xyz, 0, 0, 0)
            move_checked(h, pose)
            image = capture_pcle_view(gray=False)
            filename = f"{i}_{j}_{sample_label}.jpg"
            if not cv2.imwrite(str(out_dir / filename), image):
                raise OSError(f"Could not save {filename}")
            records[idx] = pose_to_str(pose)
        move_checked(h, home)
    except KeyboardInterrupt:
        print("Interrupted; preserving completed image records.")
    finally:
        # Stop the robot even if writing the partial trajectory fails.
        try:
            with (out_dir / "trajectory.json").open("w", encoding="utf-8") as stream:
                json.dump(records, stream, indent=4)
        finally:
            shutdown(h)
    print(f"Saved {len(records)} frames to {out_dir}")


if __name__ == "__main__":
    main()

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


"""Probe calibration cross sweep retained under its historical filename.

The active experiment translates X and then Y from -1 to +1 mm. Historical
cone-rotation alternatives remain in Git history, rather than commented code.
"""

import time


def cross_trajectory():
    """Yield the original cross scan, including the home between both axes."""
    for i in range(-10, 11):
        yield (i * 1e-4, 0.0, 0.0)
    yield (0.0, 0.0, 0.0)
    for i in range(-10, 11):
        yield (0.0, i * 1e-4, 0.0)
    yield (0.0, 0.0, 0.0)


def main():
    import smaract.smarpod as smarpod
    from smaract.smarpod import Pose

    from smarpod_pcle.hardware import SmarPod_init, move_checked, pose_to_str, shutdown

    h = None
    try:
        h = SmarPod_init()
        smarpod.SetPivot(h, [0, 0, 0])
        smarpod.SetCoordinateSystem(h, Pose(0, 0, 0, 0, 0, 0))
        for xyz in cross_trajectory():
            pose = Pose(*xyz, 0, 0, 0)
            print(f"Moving to {pose_to_str(pose)}")
            move_checked(h, pose)
            time.sleep(0.5)
    finally:
        shutdown(h)


if __name__ == "__main__":
    main()

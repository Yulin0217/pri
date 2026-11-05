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


"""Vendor-derived pose sequence; explicitly run only with full clearance."""


def main():
    import smaract.smarpod as smarpod
    from smaract.smarpod import Pose

    from smarpod_pcle.hardware import (
        SmarPod_init, check_pose_list, move_sequence, pose_to_str, shutdown,
    )

    h = None
    try:
        h = SmarPod_init()
        smarpod.SetPivot(h, [10e-3, 0, 0])
        csys = Pose(0, 0, 0, 1.5, 0, 0)
        smarpod.SetCoordinateSystem(h, csys)
        print(f"Coordinate system: {pose_to_str(csys)}")
        home = Pose(0, 0, 0, 0, 0, 0)
        sequence = [
            home,
            Pose(0, 0, 0.002, 0, 0, 0),
            Pose(0, 0, -0.002, 0, 0, 0),
            Pose(-0.002, 0, 0, 0, 0, 0),
            Pose(-0.002, -0.002, 0, 0, 0, 0),
            Pose(0.002, 0.002, 0, 0, 0, 0),
            Pose(0, 0, 0, 0, 0, -5),
            Pose(0, 0, 0, -0.02, 0, 5),
            home,
        ]
        if not check_pose_list(h, sequence):
            raise RuntimeError("Not all poses in the sequence are reachable")
        move_sequence(h, sequence)
        print(f"Final pose: {pose_to_str(smarpod.GetPose(h))}")
    finally:
        shutdown(h)


if __name__ == "__main__":
    main()

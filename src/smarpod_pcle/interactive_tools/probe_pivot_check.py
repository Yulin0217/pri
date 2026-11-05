"""Interactively verify a pivot offset using a -10 degree, 45 degree-axis tilt."""


def main():
    import smaract.smarpod as smarpod
    from smaract.smarpod import Pose

    from smarpod_pcle.robot_control import (
        SmarPod_init, compute_dRx_dRy, move_checked, shutdown,
    )

    h = None
    try:
        h = SmarPod_init()
        home = Pose(0, 0, 0, 0, 0, 0)
        smarpod.SetCoordinateSystem(h, home)
        move_checked(h, home)
        while True:
            offsets = [float(input(f"Pivot {axis} offset (mm): ")) for axis in "XYZ"]
            smarpod.SetPivot(h, [value * 1e-3 for value in offsets])
            print(f"Pivot point: {smarpod.GetPivot(h)}")
            rx, ry = compute_dRx_dRy(angle=-10, axis=45)
            move_checked(h, Pose(0, 0, 0, rx, ry, 0))
            command = input("Enter to return home and repeat; q to return home and finish: ")
            move_checked(h, home)
            if command.strip().lower() == "q":
                break
    except (KeyboardInterrupt, EOFError):
        print("\nStopped at the current pose.")
    finally:
        shutdown(h)


if __name__ == "__main__":
    main()

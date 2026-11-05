"""Jog Z by 1 mm per Enter keypress, retaining the current pose on exit."""


def main():
    import smaract.smarpod as smarpod
    from smaract.smarpod import Pose

    from smarpod_pcle.hardware import SmarPod_init, move_checked, pose_to_str, shutdown

    step_m = 1e-3
    direction = 1
    h = None
    try:
        h = SmarPod_init()
        smarpod.SetCoordinateSystem(h, Pose(0, 0, 0, 0, 0, 0))
        print("Enter: move 1 mm; u: +Z; d: -Z; q: quit. Initial direction: +Z.")
        while True:
            command = input("Move / u / d / q: ").strip().lower()
            if command == "q":
                break
            if command in ("u", "d"):
                direction = 1 if command == "u" else -1
                print(f"Direction: {'+Z' if direction == 1 else '-Z'}")
                continue
            if command:
                print("Unrecognized command; no movement.")
                continue
            current = smarpod.GetPose(h)
            target = Pose(
                current.positionX, current.positionY,
                current.positionZ + direction * step_m,
                current.rotationX, current.rotationY, current.rotationZ,
            )
            if not smarpod.IsPoseReachable(h, target):
                print("Target pose is not reachable; step skipped.")
                continue
            move_checked(h, target)
            print(f"Pose: {pose_to_str(target)}")
    except (KeyboardInterrupt, EOFError):
        print("\nStopped by user.")
    finally:
        shutdown(h)


if __name__ == "__main__":
    main()

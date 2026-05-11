import smaract.smarpod as smarpod
from smaract.smarpod import Pose

from utils_client import SmarPod_init


def pose_to_str(pose):
    return (
        f"x={pose.positionX:.6f} m, y={pose.positionY:.6f} m, z={pose.positionZ:.6f} m, "
        f"rx={pose.rotationX:.6f} deg, ry={pose.rotationY:.6f} deg, rz={pose.rotationZ:.6f} deg"
    )


def main():
    # Move 1 mm along Z per step (1 mm = 1e-3 m)
    step_m = 1e-3
    direction = 1  # 1: up, -1: down

    h = None
    try:
        h = SmarPod_init()

        csys = Pose(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        smarpod.SetCoordinateSystem(h, csys)
        print("Coordinate system set to origin.")

        print("Controls:")
        print("  Enter: move 1 mm in the current direction")
        print("  u + Enter: set direction to up (+Z)")
        print("  d + Enter: set direction to down (-Z)")
        print("  q + Enter: quit")
        print("  Default direction: up (+Z)")

        while True:
            cmd = input("Enter move / u up / d down / q quit: ").strip().lower()
            if cmd == "q":
                print("Quit.")
                break
            if cmd == "u":
                direction = 1
                print("Direction: up (+Z)")
                continue
            if cmd == "d":
                direction = -1
                print("Direction: down (-Z)")
                continue

            current_pose = smarpod.GetPose(h)
            step = direction * step_m
            target_pose = Pose(
                current_pose.positionX,
                current_pose.positionY,
                current_pose.positionZ + step,
                current_pose.rotationX,
                current_pose.rotationY,
                current_pose.rotationZ,
            )

            if not smarpod.IsPoseReachable(h, target_pose):
                print("Target pose is not reachable; step skipped.")
                continue

            smarpod.Move(h, target_pose, 0, True)
            dir_text = "up" if direction > 0 else "down"
            print(f"Moved 1 mm {dir_text}. Current pose: {pose_to_str(target_pose)}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if h is not None:
            try:
                smarpod.Stop(h)
            except Exception:
                pass
            try:
                smarpod.Close(h)
            except Exception:
                pass
            print("Device stopped and connection closed.")


if __name__ == "__main__":
    main()

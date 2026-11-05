"""Local mosaicking from commanded stage positions and calibrated metres per pixel.

Placement uses the requested XY pose, rather than measured image displacement.
"""


def main():
    from .scan_runner import run_scan
    run_scan(regression=False)


if __name__ == "__main__":
    main()

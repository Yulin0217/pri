"""Lightweight command dispatcher; help and diagnostics never initialize hardware."""

import argparse
from importlib import import_module
import sys
from .config import configure

COMMANDS = {
    "client": ("apps.client", "Visual servoing (modes 0/1) or image streaming (mode 2)"),
    "demo": ("apps.demo", "Local spiral demo with a connected server"),
    "collect-distance": ("collection.distance", "Collect grouped distance-labelled images"),
    "collect-orientation": ("collection.orientation", "Collect orientation-labelled images"),
    "collect-spiral": ("collection.spiral", "Collect a slow open-loop spiral"),
    "mosaic-direct": ("mosaicking.direct", "Mosaic using commanded stage positions"),
    "mosaic-regression": ("mosaicking.regression", "Mosaic using server displacement estimates"),
    "capture-region": ("tools.capture_region", "Preview a screen rectangle (no robot)"),
    "jog-z": ("tools.manual_z_step_control", "Interactive 1 mm Z jogs"),
    "pivot-check": ("tools.pivot_check", "Interactive probe-pivot calibration check"),
    "grid-scan": ("experiments.data_collection", "Legacy XY grid with repeated images, no Z sweep"),
    "cross-scan": ("experiments.cone_rotation", "Probe-tip calibration cross sweep"),
    "sdk-sequence": ("examples.sequence", "Vendor-derived pose-sequence example"),
    "configure-controller": ("examples.configure_controller", "Explicit one-time controller configuration"),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", metavar="PATH", help="Machine-local TOML settings")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Offline installation/configuration checks")
    doctor.add_argument("--sdk", action="store_true", help="Load SDK/library versions; never open a device")
    doctor.add_argument("--capture", action="store_true", help="Also test a live screenshot")
    doctor.add_argument("--server", action="store_true", help="Also test TCP connectivity; send no payload")
    for name, (_, description) in COMMANDS.items():
        sub = commands.add_parser(name, help=description, description=description)
        if name == "client":
            sub.add_argument("--mode", choices=("0", "1", "2"), help="Omit for interactive selection")
    args = parser.parse_args(argv)
    try:
        configure(args.config)
        if args.command == "doctor":
            from .doctor import run
            return run(check_sdk=args.sdk, check_capture=args.capture, check_server=args.server)
        module = import_module(f"smarpod_pcle.{COMMANDS[args.command][0]}")
        if args.command == "client":
            module.main(mode=args.mode)
        else:
            module.main()
        return 0
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if isinstance(exc, ImportError) and "smaract" in str(exc):
            print("Install the vendor SDK on the control PC; see docs/portability.md.", file=sys.stderr)
        return 1

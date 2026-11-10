"""Lightweight command dispatcher; help and diagnostics never initialize hardware."""

import argparse
from importlib import import_module
import sys
from .config import configure

COMMANDS = {
    "mosaic-serpentine": ("mosaicking.serpentine_mosaic", "Run a serpentine mosaic"),
    "mosaic-raster": ("mosaicking.raster_mosaic", "Run a unidirectional raster mosaic"),
    "mosaic-rings": ("mosaicking.rings_mosaic", "Run a concentric-ring mosaic"),
    "mosaic-scan": ("mosaicking.scan_patterns", "Mosaic with serpentine, raster or concentric-ring scanning"),
    "servo-client": ("applications.visual_servo_client", "Visual servoing (modes 0/1) or image streaming (mode 2)"),
    "spiral-demo": ("applications.spiral_stream_demo", "Local spiral demo with a connected server"),
    "collect-distance": ("data_collection.distance_sweep", "Collect grouped distance-labelled images"),
    "collect-orientation": ("data_collection.orientation_sweep", "Collect orientation-labelled images"),
    "collect-spiral": ("data_collection.spiral_capture", "Collect a slow open-loop spiral"),
    "mosaic-direct": ("mosaicking.direct_mosaic", "Mosaic using commanded stage positions"),
    "mosaic-regression": ("mosaicking.regression_mosaic", "Mosaic using server displacement estimates"),
    "capture-region": ("interactive_tools.screen_region_preview", "Preview a screen rectangle (no robot)"),
    "jog-z": ("interactive_tools.z_axis_jog", "Interactive 1 mm Z jogs"),
    "pivot-check": ("interactive_tools.probe_pivot_check", "Interactive probe-pivot calibration check"),
    "grid-scan": ("scan_experiments.xy_grid_capture", "Legacy XY grid with repeated images, no Z sweep"),
    "cross-scan": ("scan_experiments.xy_cross_scan", "Probe-tip calibration cross sweep"),
    "sdk-pose-sequence": ("sdk_examples.pose_sequence", "Vendor-derived pose-sequence example"),
    "configure-controller": ("sdk_examples.configure_controller", "Explicit one-time controller configuration"),
}

# Keep saved shell commands working while presenting descriptive names in --help.
COMMAND_ALIASES = {"client": "servo-client", "demo": "spiral-demo", "sdk-sequence": "sdk-pose-sequence"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", metavar="PATH", help="Machine-local TOML settings")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Offline installation/configuration checks")
    doctor.add_argument("--sdk", action="store_true", help="Load SDK/library versions; never open a device")
    doctor.add_argument("--capture", action="store_true", help="Also test a live screenshot")
    doctor.add_argument("--server", action="store_true", help="Also test TCP connectivity; send no payload")
    for name, (_, description) in COMMANDS.items():
        aliases = [alias for alias, canonical in COMMAND_ALIASES.items() if canonical == name]
        sub = commands.add_parser(name, aliases=aliases, help=description, description=description)
        if name == "servo-client":
            sub.add_argument("--mode", choices=("0", "1", "2"), help="Omit for interactive selection")
        if name in ("mosaic-scan", "mosaic-serpentine", "mosaic-raster", "mosaic-rings"):
            if name == "mosaic-scan":
                sub.add_argument("--pattern", choices=("serpentine", "raster", "rings"), default="serpentine")
            sub.add_argument("--width-um", type=float, default=1600)
            sub.add_argument("--height-um", type=float, default=1600)
            sub.add_argument("--radius-um", type=float, default=800)
            sub.add_argument("--spacing-um", type=float, default=100)
            sub.add_argument("--regression", action="store_true", help="Use server displacement with local fallback")
            sub.add_argument("--dry-run", action="store_true", help="Print XY path JSON without hardware, capture or server")
    args = parser.parse_args(argv)
    command = COMMAND_ALIASES.get(args.command, args.command)
    try:
        # Configure before importing a workflow; --help exits above without loading it.
        configure(args.config)
        if command == "doctor":
            from .doctor import run
            return run(check_sdk=args.sdk, check_capture=args.capture, check_server=args.server)
        module = import_module(f"smarpod_pcle.{COMMANDS[command][0]}")
        if command == "servo-client":
            module.main(mode=args.mode)
        elif command in ("mosaic-scan", "mosaic-serpentine", "mosaic-raster", "mosaic-rings"):
            module.main(**{key: value for key, value in vars(args).items()
                           if key not in ("command", "config")})
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

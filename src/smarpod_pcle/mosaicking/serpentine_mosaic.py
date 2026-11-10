"""Independent serpentine mosaic entry point."""

from .scan_patterns import main as run_pattern


def main(**options):
    run_pattern(pattern="serpentine", **options)


if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main as cli_main
    raise SystemExit(cli_main(["mosaic-serpentine", *sys.argv[1:]]))

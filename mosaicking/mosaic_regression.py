"""Compatibility entry point. Prefer: smarpod-pcle mosaic-regression."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["mosaic-regression", *sys.argv[1:]]))

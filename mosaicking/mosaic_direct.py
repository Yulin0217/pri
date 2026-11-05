"""Compatibility entry point. Prefer: smarpod-pcle mosaic-direct."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["mosaic-direct", *sys.argv[1:]]))

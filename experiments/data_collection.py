"""Compatibility entry point. Prefer: smarpod-pcle grid-scan."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["grid-scan", *sys.argv[1:]]))

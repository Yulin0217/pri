"""Compatibility entry point. Prefer: smarpod-pcle collect-distance."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["collect-distance", *sys.argv[1:]]))

"""Compatibility entry point. Prefer: smarpod-pcle collect-orientation."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["collect-orientation", *sys.argv[1:]]))

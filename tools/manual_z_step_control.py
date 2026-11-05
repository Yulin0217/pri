"""Compatibility entry point. Prefer: smarpod-pcle jog-z."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["jog-z", *sys.argv[1:]]))

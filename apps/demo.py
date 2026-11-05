"""Compatibility entry point. Prefer: smarpod-pcle demo."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["demo", *sys.argv[1:]]))

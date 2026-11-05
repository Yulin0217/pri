"""Compatibility entry point. Prefer: smarpod-pcle collect-spiral."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["collect-spiral", *sys.argv[1:]]))

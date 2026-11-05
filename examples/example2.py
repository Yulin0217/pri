"""Compatibility entry point. Prefer: smarpod-pcle configure-controller."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["configure-controller", *sys.argv[1:]]))

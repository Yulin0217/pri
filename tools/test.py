"""Compatibility entry point. Prefer: smarpod-pcle capture-region."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["capture-region", *sys.argv[1:]]))

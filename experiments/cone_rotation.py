"""Compatibility entry point. Prefer: smarpod-pcle cross-scan."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["cross-scan", *sys.argv[1:]]))

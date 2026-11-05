"""Compatibility entry point. Prefer: smarpod-pcle pivot-check."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["pivot-check", *sys.argv[1:]]))

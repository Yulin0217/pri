"""Compatibility entry point. Prefer: smarpod-pcle client."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["client", *sys.argv[1:]]))

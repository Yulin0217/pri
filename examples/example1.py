"""Compatibility entry point. Prefer: smarpod-pcle sdk-sequence."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["sdk-sequence", *sys.argv[1:]]))

"""Standalone raster scan; delegates to the installed package."""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["mosaic-raster", *sys.argv[1:]]))

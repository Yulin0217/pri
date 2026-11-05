"""Legacy script path; prefer ``smarpod-pcle grid-scan``.

Maintained implementation: src/smarpod_pcle/scan_experiments/xy_grid_capture.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["grid-scan", *sys.argv[1:]]))

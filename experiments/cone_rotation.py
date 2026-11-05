"""Legacy script path; prefer ``smarpod-pcle cross-scan``.

Maintained implementation: src/smarpod_pcle/scan_experiments/xy_cross_scan.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["cross-scan", *sys.argv[1:]]))

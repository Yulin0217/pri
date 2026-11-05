"""Legacy script path; prefer ``smarpod-pcle mosaic-regression``.

Maintained implementation: src/smarpod_pcle/mosaicking/regression_mosaic.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["mosaic-regression", *sys.argv[1:]]))

"""Legacy script path; prefer ``smarpod-pcle mosaic-direct``.

Maintained implementation: src/smarpod_pcle/mosaicking/direct_mosaic.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["mosaic-direct", *sys.argv[1:]]))

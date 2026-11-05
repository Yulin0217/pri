"""Legacy script path; prefer ``smarpod-pcle collect-spiral``.

Maintained implementation: src/smarpod_pcle/data_collection/spiral_capture.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["collect-spiral", *sys.argv[1:]]))

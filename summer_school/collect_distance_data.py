"""Legacy script path; prefer ``smarpod-pcle collect-distance``.

Maintained implementation: src/smarpod_pcle/data_collection/distance_sweep.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["collect-distance", *sys.argv[1:]]))

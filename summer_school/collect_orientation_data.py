"""Legacy script path; prefer ``smarpod-pcle collect-orientation``.

Maintained implementation: src/smarpod_pcle/data_collection/orientation_sweep.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["collect-orientation", *sys.argv[1:]]))

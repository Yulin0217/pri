"""Legacy script path; prefer ``smarpod-pcle spiral-demo``.

Maintained implementation: src/smarpod_pcle/applications/spiral_stream_demo.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["spiral-demo", *sys.argv[1:]]))

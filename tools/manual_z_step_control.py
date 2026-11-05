"""Legacy script path; prefer ``smarpod-pcle jog-z``.

Maintained implementation: src/smarpod_pcle/interactive_tools/z_axis_jog.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["jog-z", *sys.argv[1:]]))

"""Legacy script path; prefer ``smarpod-pcle pivot-check``.

Maintained implementation: src/smarpod_pcle/interactive_tools/probe_pivot_check.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["pivot-check", *sys.argv[1:]]))

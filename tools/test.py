"""Legacy script path; prefer ``smarpod-pcle capture-region``.

Maintained implementation: src/smarpod_pcle/interactive_tools/screen_region_preview.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["capture-region", *sys.argv[1:]]))

"""Legacy script path; prefer ``smarpod-pcle configure-controller``.

Maintained implementation: src/smarpod_pcle/sdk_examples/configure_controller.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["configure-controller", *sys.argv[1:]]))

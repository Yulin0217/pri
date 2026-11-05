"""Legacy script path; prefer ``smarpod-pcle servo-client``.

Maintained implementation: src/smarpod_pcle/applications/visual_servo_client.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["servo-client", *sys.argv[1:]]))

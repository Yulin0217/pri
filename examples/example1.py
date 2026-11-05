"""Legacy script path; prefer ``smarpod-pcle sdk-pose-sequence``.

Maintained implementation: src/smarpod_pcle/sdk_examples/pose_sequence.py.
This adapter retains existing launch scripts; add application logic there.
"""

if __name__ == "__main__":
    import sys
    from smarpod_pcle.cli import main
    raise SystemExit(main(["sdk-pose-sequence", *sys.argv[1:]]))

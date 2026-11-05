"""Non-moving diagnostic checks for development and control computers."""

from importlib import import_module, metadata
import json
from pathlib import Path
import platform
import socket
import sys
import tempfile

from .config import get_settings


def run(*, check_sdk=False, check_capture=False, check_server=False):
    settings = get_settings()
    print(f"Python {platform.python_version()} | {platform.system()} {platform.machine()}")
    print(f"Interpreter: {sys.executable}")
    print("Effective settings:")
    print(json.dumps(settings.as_dict(), indent=2))
    failed = False

    def check(name, action):
        nonlocal failed
        try:
            detail = action()
            print(f"[OK] {name}: {detail}")
        except Exception as exc:
            failed = True
            print(f"[FAIL] {name}: {exc}")

    for distribution, module in (("numpy", "numpy"), ("opencv-python", "cv2"), ("mss", "mss")):
        def dependency(dist=distribution, mod=module):
            import_module(mod)
            return metadata.version(dist)
        check(distribution, dependency)

    def output_check():
        root = Path(settings.output_dir).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=root) as probe:
            probe.write(b"smarpod-pcle write check")
        return str(root.resolve())
    check("Output directory writable", output_check)

    if check_sdk:
        def sdk_check():
            from .hardware import check_lib_compatibility, get_sdk
            check_lib_compatibility()
            sdk = get_sdk()
            return f"API {sdk.api_version}; library {sdk.GetDLLVersion()} (no device opened)"
        check("SmarAct SDK", sdk_check)
    else:
        print("[SKIP] SmarAct SDK/device access (use --sdk on the control PC)")
    if check_capture:
        def capture_check():
            from .capture import capture_pcle_view
            image = capture_pcle_view()
            return f"Captured {image.shape}; visually verify ROI with capture-region"
        check("Screen capture", capture_check)
    if check_server:
        def server_check():
            with socket.create_connection((settings.server.host, settings.server.port),
                                          timeout=settings.server.timeout_s):
                return "TCP connected; protocol/model not verified"
        check("Inference server", server_check)
    print("No controller was opened, configured, calibrated, referenced or moved.")
    return 1 if failed else 0

"""Offline import, diagnostics and controller lifecycle regression checks."""

from contextlib import redirect_stdout
import importlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from smarpod_pcle import doctor, hardware
from smarpod_pcle.config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InstallationTests(unittest.TestCase):
    def test_every_command_and_original_script_import_is_passive(self):
        # Use a fresh interpreter so cached modules cannot hide import-time behavior
        # and guards do not leave mocked aliases in other tests' imported modules.
        check = r'''
import builtins
import importlib
from pathlib import Path
import runpy
import socket

import cv2
import mss

from smarpod_pcle import capture, hardware
from smarpod_pcle.cli import COMMANDS

def forbidden(*args, **kwargs):
    raise AssertionError("Import attempted SDK/input/socket/screen access")

original_import = builtins.__import__
original_import_module = importlib.import_module

def guarded_import(name, *args, **kwargs):
    if name == "smaract" or name.startswith("smaract."):
        forbidden()
    return original_import(name, *args, **kwargs)

def guarded_import_module(name, *args, **kwargs):
    if name == "smaract" or name.startswith("smaract."):
        forbidden()
    return original_import_module(name, *args, **kwargs)

builtins.__import__ = guarded_import
importlib.import_module = guarded_import_module
builtins.input = forbidden
hardware.get_sdk = forbidden
socket.socket = forbidden
socket.create_connection = forbidden
mss.mss = forbidden
cv2.imshow = forbidden
capture.capture_partial_screen = forbidden
capture.capture_pcle_view = forbidden
capture.capture_mosaic_view = forbidden

for module, _ in COMMANDS.values():
    importlib.import_module("smarpod_pcle." + module)

wrappers = []
for directory in ("apps", "common", "examples", "experiments", "mosaicking", "summer_school", "tools"):
    wrappers.extend(sorted(Path(directory).rglob("*.py")))
assert len(wrappers) >= 20, "Original entry points were not found"
for wrapper in wrappers:
    runpy.run_path(str(wrapper), run_name="__import_check__")
print(f"Imported {len(COMMANDS)} commands and {len(wrappers)} original scripts safely")
'''
        result = subprocess.run(
            [sys.executable, "-c", check], cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("original scripts safely", result.stdout)

    def test_default_doctor_does_not_load_sdk_connect_or_capture(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(doctor, "get_settings", return_value=Settings(output_dir=directory)), \
             patch.object(doctor, "import_module", wraps=importlib.import_module) as imports, \
             patch.object(hardware, "get_sdk", side_effect=AssertionError("SDK access")) as sdk, \
             patch("socket.create_connection", side_effect=AssertionError("Network access")) as connect, \
             patch("mss.mss", side_effect=AssertionError("Screen access")) as capture, \
             redirect_stdout(output):
            result = doctor.run()
        self.assertEqual(result, 0, output.getvalue())
        self.assertEqual([call.args[0] for call in imports.call_args_list], ["numpy", "cv2", "mss"])
        sdk.assert_not_called()
        connect.assert_not_called()
        capture.assert_not_called()
        self.assertIn("[SKIP] SmarAct SDK", output.getvalue())

    def test_missing_sdk_diagnostic_returns_failure_without_traceback(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(doctor, "get_settings", return_value=Settings(output_dir=directory)), \
             patch.object(hardware, "import_module", side_effect=ModuleNotFoundError("smaract")), \
             patch("socket.create_connection", side_effect=AssertionError("Network access")), \
             patch("mss.mss", side_effect=AssertionError("Screen access")), \
             redirect_stdout(output):
            result = doctor.run(check_sdk=True)
        self.assertEqual(result, 1)
        self.assertIn("[FAIL] SmarAct SDK", output.getvalue())
        self.assertIn("Install the matching SmarAct", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_partial_startup_failure_stops_and_closes_open_handle(self):
        sdk = SimpleNamespace(
            api_version=(1, 0, 0), GetDLLVersion=Mock(return_value=(1, 0, 0)),
            Open=Mock(return_value="handle"),
            Property=SimpleNamespace(FREF_AND_CAL_FREQUENCY=1),
            Set_ui=Mock(side_effect=RuntimeError("sensor setup failed")),
            Stop=Mock(), Close=Mock(),
        )
        with patch.object(hardware, "get_sdk", return_value=sdk), \
             patch.object(hardware, "get_settings", return_value=Settings()), \
             patch("builtins.input", return_value="0"), \
             redirect_stdout(io.StringIO()), \
             self.assertRaisesRegex(RuntimeError, "sensor setup failed"):
            hardware.SmarPod_init()
        sdk.Stop.assert_called_once_with("handle")
        sdk.Close.assert_called_once_with("handle")

    def test_close_still_runs_when_stop_raises(self):
        sdk = SimpleNamespace(Stop=Mock(side_effect=RuntimeError("stop failed")), Close=Mock())
        with patch.object(hardware, "get_sdk", return_value=sdk), \
             self.assertRaisesRegex(RuntimeError, "stop failed"):
            hardware.shutdown("handle")
        sdk.Close.assert_called_once_with("handle")


if __name__ == "__main__":
    unittest.main()

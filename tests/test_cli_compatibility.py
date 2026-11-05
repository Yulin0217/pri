"""Command renames must preserve existing launch commands without touching hardware."""

from contextlib import redirect_stdout
import io
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import Mock, patch

from smarpod_pcle import cli


class CommandCompatibilityTests(unittest.TestCase):
    def test_old_and_new_names_dispatch_identically(self):
        for alias, canonical in cli.COMMAND_ALIASES.items():
            for name in (alias, canonical):
                with self.subTest(command=name):
                    workflow = Mock()
                    options = ["--mode", "2"] if canonical == "servo-client" else []
                    with patch.object(cli, "configure") as configure, \
                         patch.object(cli, "import_module", return_value=workflow) as load:
                        result = cli.main(["--config", "machine.toml", name, *options])
                    self.assertEqual(result, 0)
                    configure.assert_called_once_with("machine.toml")
                    load.assert_called_once_with("smarpod_pcle." + cli.COMMANDS[canonical][0])
                    if canonical == "servo-client":
                        workflow.main.assert_called_once_with(mode="2")
                    else:
                        workflow.main.assert_called_once_with()

    def test_all_command_help_avoids_configuration_and_workflow_import(self):
        for command in ("doctor", *cli.COMMANDS, *cli.COMMAND_ALIASES):
            with self.subTest(command=command), \
                 patch.object(cli, "configure") as configure, \
                 patch.object(cli, "import_module") as load, \
                 redirect_stdout(io.StringIO()), \
                 self.assertRaises(SystemExit) as stopped:
                cli.main([command, "--help"])
            self.assertEqual(stopped.exception.code, 0)
            configure.assert_not_called()
            load.assert_not_called()

    def test_original_client_script_preserves_arguments(self):
        script = Path(__file__).resolve().parents[1] / "apps/client.py"
        with patch.object(cli, "main", return_value=0) as dispatch, \
             patch.object(sys, "argv", [str(script), "--mode", "2"]), \
             self.assertRaises(SystemExit) as stopped:
            runpy.run_path(str(script), run_name="__main__")
        self.assertEqual(stopped.exception.code, 0)
        dispatch.assert_called_once_with(["servo-client", "--mode", "2"])


if __name__ == "__main__":
    unittest.main()

# Development

## Boundaries

`src/smarpod_pcle` is the installable implementation. Root-level script folders
are compatibility adapters. Use the `smarpod-pcle` CLI for new workflows and keep
machine settings in TOML instead of adding host addresses or screen coordinates
to individual scripts.

- `config` validates settings before command dispatch; unknown fields fail early.
- `geometry`, transport framing, and mosaic primitives can run without the SDK.
- `hardware.get_sdk()` is the explicit vendor-loading boundary. Importing modules
  must not prompt, connect, calibrate, reference, or move a controller.
- `hardware.SmarPod_init()` opens/configures a handle and cleans up partially
  completed initialization. `shutdown()` attempts Close even if Stop fails.
- `move_checked()` rejects non-finite and unreachable poses. Reachability is not
  collision checking, and the code does not infer a physical safety envelope.
- The servo main thread owns movement. Network workers communicate whole reply
  records through queues; sockets/workers stop before the controller is closed.
- Shared capture uses both rectangles from the active configuration. Shared
  output helpers create distinct run directories and check image-write success.
- `mosaicking.scan` owns the common hardware/file lifecycle. Geometry and network
  displacement sources are independently testable.

The preserved servo policy is experimental: rotation updates include a random
reset. This refactor does not replace it with a new control algorithm. Orientation
dataset offsets likewise preserve the original projection approximation. Any
future control-policy change needs separate numerical and hardware validation.

## Checks

Install with `python -m pip install -e ".[dev]"`, then run:

```bash
python -m ruff check src tests
python -m pytest
python -m smarpod_pcle doctor
python -m build
python -m pip check
```

Pytest discovers only `tests/`, avoiding accidental execution of historical
files named `test.py` or `robot_test.py`. Tests cover fragmented/disconnected
transport, reference/fallback behavior, configuration, mosaic placement, manual
focus references, persistence failures, import behavior and client shutdown.
Robot interactions use fake SDKs; network tests use local socket pairs. Default
diagnostics never call SDK, capture, or network operations.

The CI workflow describes an offline OS/Python matrix. Local passes are not
proof of remote CI success, vendor ABI compatibility, or real hardware behavior.
The dependency recipe uses bounded compatible version ranges, not a fully locked
cross-platform environment. For reproducible experiments, save `python -m pip
freeze` and the vendor SDK/firmware versions alongside the dataset. A frozen Mac
environment should not be copied as a Windows/Linux native installation.

## Changes from the previous script layout

- Machine settings are centralized, and output defaults to `runs/`.
- Legacy script paths require the project to be installed and delegate to the CLI.
- Imports and help no longer initialize hardware. Streaming mode 2 needs no SDK.
- Interrupted/error cleanup stops and closes without automatic homing.
- Servo errors terminate the run; partial TCP headers are read correctly. Replies
  must be finite and cannot request nonzero distance and angle simultaneously.
- Distance groups store their focus references; orientation uses the actual
  focused pose instead of silently replacing it with coordinate zero.
- Regression sends its reference image and falls back for the rest of a run after
  a failure, without reusing an invalid TCP stream.
- Legacy XY scan logs retain every capture index instead of overwriting one.

These are deliberate behavior changes. Review the applicable workflow and
commission it on the actual setup before resuming experiments.

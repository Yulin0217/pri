# SmarPod pCLE Control

Python client tools for a SmarAct **SmarPod** six-axis positioner carrying a
probe-based confocal laser endomicroscopy (**pCLE**) probe. The project captures
the visible pCLE image, collects labelled datasets, stitches mosaics, and can
apply corrections from an external inference server.

The robot SDK, controller drivers, pCLE acquisition software, inference server,
and trained weights are **not included**. The current Mac is a development
computer, not the robot-control computer. Offline checks do not validate motion.
See [running on another computer](docs/portability.md) for the full deployment
requirements and vendor/platform references.

## Quick start: development without a robot

From the repository root, on the `yulin` branch:

```bash
conda env create -f environment.yml
conda activate smarpod-pcle
smarpod-pcle doctor
python -m pytest
```

This creates a separate Python 3.12 environment and installs the project in
editable mode with development tools. No vendor SDK is needed for these checks;
they do not open a controller, capture the screen, or contact an inference server.
The tests use fake hardware and local socket pairs.

Without conda, use Python 3.11 or newer in a virtual environment:

```bash
python -m venv .venv
# Activate .venv using the command for your shell, then:
python -m pip install -e ".[dev]"
```

Use `python -m smarpod_pcle` wherever `smarpod-pcle` is shown if the executable is
not on your PATH. `pip install -r requirements.txt` installs the runtime project;
the old `environment.txt` remains a compatible pip entry point.

## Configuration

Copy [config/example.toml](config/example.toml) to `config/local.toml` and edit it
for the destination computer. Do not reuse the sample screen coordinates or
probe geometry without checking them. Local configuration is git-ignored.

```bash
smarpod-pcle --config config/local.toml doctor
smarpod-pcle --config config/local.toml client --mode 2
```

The second command actually captures the screen and connects to the configured
server, but does not load the robot SDK or move the robot.

Configuration resolution is: `--config PATH`, then `SMARPOD_PCLE_CONFIG`, then
`config/local.toml` in the current working directory, then built-in defaults.
An explicitly supplied missing or invalid configuration is an error. Place
`--config` **before** the command. Use an absolute config path when launching
outside the checkout.

| Section | Settings |
| --- | --- |
| `robot` | Model code, locator, speed in m/s, maximum frequency in Hz, probe-tip pivot Z in metres |
| `server` | Trusted host, TCP port, timeout in seconds; default host is localhost |
| `capture.pcle_view` | Live-view rectangle: `top`, `left`, `width`, `height`, in screen pixels |
| `capture.mosaic_view` | Viewer mosaic rectangle used for client/demo logging |
| `mosaic` | Metres per pixel, image/stage axis signs, blend mode, regression units |
| `output_dir` | Root for captured data and logs |

Relative output paths in a TOML file are resolved against that file's directory.
With no file, output defaults to `runs/` in the current working directory.
New runs use timestamped directories including microseconds and never reuse an
existing run directory. Individual workflows retain their scan constants in the
corresponding source module; these are distinct from machine-specific settings.

Some calibration/legacy workflows intentionally override robot defaults:
`sdk-sequence` uses a 10 mm X pivot, a coordinate-system X rotation of 1.5°, and
motions reaching ±2 mm; it does not use the probe-tip pivot. `grid-scan` and
`cross-scan` set a zero pivot; `pivot-check` uses the entered offsets.
`collect-spiral` sets its own 25 µm/s speed and leaves the existing pivot unless
`PIVOT_XYZ` is set in its recipe. Direct mosaicking caps configured speed at
2 mm/s. The shared initializer sets pivot mode, but only servo/demo and the two
labelled collectors automatically apply `robot.probe_tip_z_m`.

## Commands

Run `smarpod-pcle --help` for the command list. Every command supports `--help`
without hardware or SDK access.

| Command | Purpose | Robot | Server |
| --- | --- | --- | --- |
| `doctor` | Package, config and output checks | No | No by default |
| `capture-region` | Interactive screen-rectangle preview | No | No |
| `client --mode 2` | Stream pCLE frames only | No | Required |
| `client --mode 0` | Visual servoing while following a local XY spiral | Yes | Required |
| `client --mode 1` | Visual servoing from a prompted initial offset | Yes | Required |
| `demo` | Local spiral; drain server replies without using them for movement | Yes | Required |
| `collect-distance` | Groups of Z-offset images from a manual focus reference | Yes | No |
| `collect-orientation` | Tilt-labelled images relative to a manual focus reference | Yes | No |
| `collect-spiral` | Slow open-loop scan with images and positions | Yes | Optional, disabled by default |
| `mosaic-direct` | Stitch using commanded stage positions | Yes | No |
| `mosaic-regression` | Stitch using inferred frame displacement | Yes | Attempts connection; local fallback |
| `jog-z` | Enter to jog Z by 1 mm; `u`/`d` set direction; `q` exits | Yes | No |
| `pivot-check` | Interactive pivot-offset and tilt check | Yes | No |
| `grid-scan` | Legacy XY grid with repeated images at fixed Z | Yes | No |
| `cross-scan` | X/Y cross sweep for probe-tip calibration | Yes | No |
| `sdk-sequence` | Vendor-derived pose-sequence example | Yes | No |
| `configure-controller` | Explicit, one-time persistent controller setup | Yes | No |

Omitting `client --mode` prompts for a mode. Client modes can be stopped with
`q` + Enter or Ctrl-C. Other workflows use Ctrl-C unless their prompt provides
an exit command. The client preserves the original experimental orientation
correction rule, including its random reset to an angle in `[0, 2)` degrees;
it is not a calibrated general-purpose controller.

### Control-computer setup

1. Install the matching SmarAct native runtime, drivers, and Python bindings for
   the controller, OS, CPU architecture, and Python interpreter. The public
   SmarPod SDK offering lists Windows and Linux; this project does not establish
   Mac hardware support. Follow the exact SDK release's requirements.
2. Install and open the pCLE acquisition/viewer software in a graphical session.
3. Set the model, locator, calibrated pivot, display rectangles, and pixel scale
   in the local configuration. Preview the rectangle with `capture-region`.
4. If required, start a compatible inference service and configure its host/port.
5. Use the opt-in diagnostics below, then commission the hardware separately.

```bash
smarpod-pcle --config config/local.toml doctor --sdk
smarpod-pcle --config config/local.toml doctor --capture
smarpod-pcle --config config/local.toml doctor --server
```

`--sdk` loads the API/native library and checks major versions without opening a
device. `--capture` takes a real screenshot. `--server` opens and closes a TCP
connection without sending images or validating a model. These flags can be
combined. Details and troubleshooting are in [portability.md](docs/portability.md).

**Movement lifecycle:** initialization can calibrate sensors (when selected) and
reference an unreferenced stage. `configure-controller` always calibrates after
writing configuration. Operational commands check pose reachability,
which does not detect contact or collisions. Completed scans may return to home
or their focus reference. Errors, cancellation, and cleanup call Stop/Close
without adding an automatic return-home move. Confirm physical clearance for the
actual trajectory, and use the controller's physical stop procedure if needed.

### Data collection and outputs

See [the collection guide](docs/data-collection.md) for scan parameters, reference
poses, coordinate conventions, and `labels.json` examples.

- Distance collection defaults to `0..200 µm` in `10 µm` steps, with a new manual
  focus reference for each group. It returns to that reference after each group.
- Orientation collection defaults to axes `0..180°` in `30°` steps and angles
  `−10..10°` in `2°` steps. The measured reference XYZ/rotation is retained, and
  calculated X/Y rotation offsets are added to its Euler components.
- The legacy grid intentionally captures 41 repeated frames at each XY point;
  the old filename suffix resembles a Z offset, but no Z sweep is commanded.
  Use `collect-distance` for actual distance-labelled data.
- Direct/regression mosaics save raw `frames/`, `mosaic.png`, and `trajectory.json`.
  Calibration determines their geometric accuracy. Regression sends the first
  frame as a reference and switches permanently to commanded displacement if
  communication or reply validation fails. A fixed canvas can clip model drift;
  raw frames are retained and wholly outside placements are reported.
- Servo runs save `state.json` and mosaic-view screenshots; demo runs save both
  the live and mosaic views. The slow spiral saves images and `positions.txt`.

### Network contract

Messages are length-prefixed Python pickle objects with JPEG-encoded 224×224
images. Servo replies contain `distance`, `angle`, `axis`; regression replies
contain `dx`, `dy`. Units, `signal` semantics, timeouts and fallback behavior are
specified in [protocol.md](docs/protocol.md). Only connect to a trusted server:
this legacy protocol has no authentication or encryption and unpickling can
execute code. The server implementation and weights must be supplied separately.

## Repository structure

```text
config/example.toml           Machine configuration template
docs/                        Deployment, data collection, protocol, development
src/smarpod_pcle/
  cli.py, doctor.py           Entry point and non-moving checks
  config.py                  Validated TOML configuration
  hardware.py, geometry.py   SDK lifecycle and independent coordinate math
  capture.py, net.py         Shared screen and TCP operations
  output.py                  Run directories and checked image writes
  apps/                      Visual-servoing client and spiral demo
  collection/                Distance, orientation, slow spiral and helpers
  mosaicking/                Canvas primitives and shared scan lifecycle
  tools/                     Screen preview, Z jogging, pivot check
  experiments/               Legacy grid and calibration cross sweep
  examples/                  Explicit vendor-derived setup/sequence examples
tests/                       Hardware-free regression and installation tests
apps/, common/, ...          Compatibility entry points/imports
pyproject.toml               Package metadata, dependencies, CLI and test config
environment.yml              Portable conda development environment recipe
```

The original paths still run after installation, for example
`python apps/client.py --mode 2` or `python summer_school/collect_distance_data.py`.
They delegate to the installed package; do not edit them to change application
logic. For global `--config`, use the CLI or `SMARPOD_PCLE_CONFIG`.

## Development and verification

```bash
python -m ruff check src tests
python -m pytest
python -m build
python -m pip check
```

See [development.md](docs/development.md) for design boundaries and tests. CI is
configured to run offline checks on Windows, Linux and macOS with Python 3.11/3.12;
adding the workflow does not mean those remote jobs have run yet.

Locally verified on this development Mac: Python 3.12 environment creation,
editable installation, CLI/default diagnostics, unit tests, lint, and package
build. The vendor SDK, actual controller, pCLE display capture, and inference
service require separate validation on the control setup.

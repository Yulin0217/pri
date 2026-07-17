# SmarPod pCLE Probe Control — Client

Client-side control code for a SmarAct **SmarPod** 6-DoF micro-positioner carrying a
pCLE (probe-based confocal laser endomicroscopy) probe. The laptop is connected to the
SmarPod controller over USB. The scripts capture the pCLE viewer region of the screen
with `mss`, stream the frames over TCP to a remote inference server (the "AGX station"),
and — in the visual-servoing modes — apply the distance / angle corrections returned by
the server to the robot pose.

> **Safety:** every script in this repository moves the positioner. Before running
> anything, make sure the probe has enough clearance and cannot collide with the sample
> or the optics.

## Repository layout

```
.
├── apps/                        # Main client applications (talk to the AGX server)
│   ├── client.py                # Visual-servoing client with three run modes
│   └── demo.py                  # Spiral-mosaic demo (sends images, ignores server replies)
├── common/
│   ├── utils_client.py          # Shared helpers: SmarPod_init(), axis-angle -> (dRx, dRy), pose printing
│   └── capture.py               # Screen capture of the pCLE live view (mss)
├── experiments/                 # Standalone data-collection / motion scripts (no server needed)
│   ├── cone_rotation.py         # Probe-tip calibration sweeps; cone-rotation variants kept commented out
│   └── data_collection.py       # XY grid scan collecting pCLE screenshots (clear/blur dataset)
├── tools/                       # Interactive helpers
│   ├── manual_z_step_control.py # Jog the Z axis in 1 mm steps from the keyboard
│   ├── robot_test.py            # Interactive pivot-point / tilt check
│   └── test.py                  # Screenshot-region finder (pick capture coordinates)
├── examples/                    # SmarAct SDK programming examples (lightly adapted)
│   ├── example1.py              # Pose-sequence example
│   └── example2.py              # One-time controller configuration (ConfigureController)
├── summer_school/               # Data-collection scripts + guide for distance/orientation labels
│   ├── collect_distance_data.py    # Sweep Z, capture pCLE frames labelled with defocus distance
│   ├── collect_orientation_data.py # Tilt probe over (axis, angle), capture labelled frames
│   ├── collection_utils.py         # Shared setup: pivot at tip, save labels.json
│   └── README.md                   # Detailed data-collection guide
├── environment.txt              # Python dependencies (pip requirements format)
└── README.md
```

All entry scripts insert the repository root into `sys.path` at startup, so they can be
run directly from any working directory, e.g. `python apps/client.py`.

## Environment

- Python 3.12 (CPython); other recent 3.x versions should work.
- Pip packages: `pip install -r environment.txt` (numpy, opencv-python, mss).
- **SmarAct SmarPod Python API** (`smaract.smarpod`): not on PyPI. Install it from the
  SmarAct SDK shipped with the controller. The Python API and the shared library must
  have the same major version — this is checked at startup.

## First-time hardware setup

1. Find the USB locator with `smarpod.FindSystems()` (usually `usb:ix:0`).
2. Configure the controller once for your SmarPod model code (here `10001`):
   `smarpod.ConfigureController(10001, locator)` — see `examples/example2.py`.
3. Open the device with `smarpod.Open(10001, locator)`.

`common/utils_client.py::SmarPod_init()` wraps the regular startup used by the apps and
tools: open, optional sensor calibration (asked interactively), referencing if needed,
speed 3 mm/s, max piezo frequency 18.5 kHz, pivot mode `RELATIVE`.

## Client-server protocol

Every message is a 4-byte big-endian `uint32` length prefix followed by a `pickle`
payload:

- client → server: `{'image': <JPEG bytes, 224x224 grayscale>, 'signal': 0 | 1}`
- server → client: `{'distance': float, 'angle': float, 'axis': float}`

Set `HOST` / `PORT` at the top of `apps/client.py` and `apps/demo.py` to match the AGX
station (default `172.30.28.159:12334`).

Screen-capture rectangles are hard-coded: pCLE live view at `top=45, left=1118,
350x350`; mosaic view at `top=420, left=1050, 600x600`. Use `tools/test.py` to find the
right coordinates for your screen layout.

## Applications

### `apps/client.py` — visual-servoing client

```bash
python apps/client.py
```

Initializes the SmarPod (pivot point set 37.4 mm below the platform origin, i.e. at the
probe tip), then asks for a run mode:

| Mode | Name | Behaviour |
|------|------|-----------|
| `0` | Visual servoing + mosaicing | Follows a local spiral XY trajectory; at each waypoint streams frames, applies the server's distance/angle corrections, and advances once the server reports no correction |
| `1` | Visual servoing | Moves to a user-given initial axis/angle/z offset, then continuously applies server corrections |
| `2` | Controller | Only streams frames to the server; no robot motion |

Three daemon threads run concurrently (frame sender, reply receiver, robot control).
Press `q` + Enter (or Ctrl-C) to stop; the robot returns home and the device is closed.
Each run writes `robot_state_<timestamp>/` containing `state.json` (per-step pose log)
and `images/img_*.png` (mosaic-view screenshots).

### `apps/demo.py` — spiral-mosaic demo

```bash
python apps/demo.py
```

Moves along a local spiral trajectory (`x = i cos(1.12 i pi) * 1e-4`,
`y = i sin(1.12 i pi) * 1e-4`, denser sampling on the outer rings), captures the live
frame and the mosaic view at every waypoint, and sends each frame to the server with
`signal = 1`.

**Important:** server replies are read only to keep the socket drained — they are *not*
used for motion. The trajectory is fully local. Output goes to
`mosaic_demo_<timestamp>/images/` (`img_*.png` mosaic view, `frame_*.png` live frame).

## Experiments (offline, no server)

- `experiments/data_collection.py` — asks for a save directory, then scans a 21x21 XY
  grid (±1 mm, 0.1 mm pitch), saving pCLE screenshots as `<i>_<j>_<n>.jpg` into
  `<save_dir>/clear_blur_data<timestamp>/` together with `trajectory.json`. The inner
  Z sweep (`n` = 0…400 µm) is currently disabled in the commanded pose and only appears
  in the file names. Commented-out variants: distance-blur series, orientation-blur
  series, spiral scan, manual capture.
- `experiments/cone_rotation.py` — active part runs a ±1 mm cross sweep along X then Y
  for probe-tip calibration. The cone-rotation sweeps (fixed angle, varying axis, using
  `compute_dx_dy_dz_dRx_dRy`) are kept as commented-out blocks.

## Data collection (Summer School)

`summer_school/` contains two scripts that build labelled training sets for the models
used by the visual-servoing client, plus a detailed guide (`summer_school/README.md`):

- `collect_distance_data.py` — sweeps the probe along Z from a user-set focus plane and
  labels each captured pCLE frame with its defocus distance (µm).
- `collect_orientation_data.py` — tilts the probe over a grid of `(axis, angle)`
  orientations (via `compute_dRx_dRy`) and labels each captured frame.

Each run writes a timestamped `distance_data_*/` or `orientation_data_*/` directory with
an `images/` folder and a `labels.json`. See `summer_school/README.md` for setup,
calibration, configuration, and the label format.

## Tools

- `tools/manual_z_step_control.py` — Enter = move 1 mm along Z, `u`/`d` = set direction
  up/down, `q` = quit. Checks pose reachability before each step.
- `tools/robot_test.py` — interactively set a pivot-point offset (mm), tilt the probe
  −10° about the 45° axis, and return home. Used to verify the pivot calibration.
- `tools/test.py` — enter screen coordinates and preview the captured region; use it to
  update the hard-coded capture rectangles in `apps/` and `experiments/`.

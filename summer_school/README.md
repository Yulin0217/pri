# Summer School — pCLE Probe Data Collection

Two scripts that collect supervised training data for the pCLE (probe-based confocal
laser endomicroscopy) probe mounted on the SmarAct **SmarPod** positioner:

| Script | Label collected | Trains the model that predicts... |
|--------|-----------------|-----------------------------------|
| `collect_distance_data.py` | defocus distance (µm) | how far the probe is from the tissue surface |
| `collect_orientation_data.py` | tilt `axis` + `angle` (deg) | the probe orientation relative to the surface |

These are exactly the quantities the inference server returns to `apps/client.py`
(`distance`, `angle`, `axis`) during visual servoing. Collecting clean, well-labelled
data here is what makes that closed loop work.

---

## 1. Background: what the labels mean

The probe is held by the SmarPod with its **rotation pivot placed at the probe tip**, so
tilting the probe rotates it about the tip without translating the contact point.

- **Distance.** A pCLE image is sharpest when the probe tip sits on the sample's focus
  plane. Moving the tip away from that plane blurs the image. The *distance* label is the
  defocus distance in micrometres. By convention the probe moves along **−Z** to increase
  distance, matching `apps/client.py` (mode 1 uses `t = [0, 0, -z_distance*1e-6]`).
- **Orientation.** A pCLE image is sharp and symmetric when the probe axis is aligned with
  the surface normal (`angle = 0`). Tilting the probe by `angle` degrees in an azimuth
  direction `axis` produces directional blur. `compute_dRx_dRy(angle, axis)` converts the
  `(axis, angle)` tilt into the SmarPod's `(dRx, dRy)` rotation about the X and Y axes.

---

## 2. Prerequisites

**Hardware.** SmarPod controller connected over USB, pCLE probe mounted, a sample in
view, and enough clearance for the probe to move over the full sweep range.

**Software.** From the repository root:

```bash
pip install -r environment.txt        # numpy, opencv-python, mss
```

The SmarAct SmarPod Python API (`smaract.smarpod`) is **not** on PyPI — install it from
the SmarAct SDK shipped with the controller. The Python API and the shared library must
share the same major version (checked at startup).

**Calibrate three things before collecting** (each only changes rarely):

1. **Screen-capture region.** The pCLE live view is read from the screen. Run
   `python tools/test.py`, find the rectangle covering the live view, and set it in
   `common/capture.py` → `PCLE_VIEW`.
2. **Probe-tip pivot.** `PROBE_TIP_Z_M` in `summer_school/collection_utils.py` is the
   distance (m) from the SmarPod platform origin down to the probe tip (default
   `37.4e-3`). Verify it with `python tools/robot_test.py` — with a correct pivot the tip
   stays fixed while the probe tilts.
3. **Focus reference plane.** Both scripts pause and ask you to bring the probe into best
   focus by hand; that pose becomes the zero reference. No code change needed.

---

## 3. Coordinate & sign conventions

- **Z axis:** negative Z moves the probe away from the surface (increasing defocus
  distance); positive Z moves toward it.
- **axis** ∈ `[0, 180]` deg — azimuth of the tilt direction in the XY plane
  (`0` → tilt about X, `90` → tilt about Y).
- **angle** ∈ `[-10, 10]` deg — tilt of the probe axis away from the surface normal.
  Note `(axis, +angle)` and `(axis + 180, -angle)` describe the same physical pose, so
  sweeping `axis` over `[0, 180]` together with signed `angle` contains some redundancy at
  the end points; narrow the ranges if you want a strictly unique grid.
- With the pivot at the tip, tilts keep the tip fixed; only its orientation changes.

---

## 4. `collect_distance_data.py`

Translates the probe from the focus plane along Z in fixed steps, capturing and labelling
one or more frames per step.

```bash
python summer_school/collect_distance_data.py
```

Configuration constants at the top of the file:

| Constant | Default | Meaning |
|----------|---------|---------|
| `Z_STEP_UM` | `5.0` | step size along Z (µm) |
| `Z_MAX_UM` | `200.0` | largest defocus distance from the focus plane (µm) |
| `Z_DIRECTION` | `-1` | `-1` = move along −Z (away from surface) |
| `FRAMES_PER_STEP` | `1` | frames captured at each Z position |
| `SETTLE_S` | `0.5` | pause after each move before capturing (s) |

Flow: init SmarPod → set pivot at tip → prompt you to focus → step `0, Z_STEP_UM, …,
Z_MAX_UM`, capturing frames labelled with the defocus distance → return home → save.

---

## 5. `collect_orientation_data.py`

Tilts the probe over a grid of `(axis, angle)` orientations, capturing and labelling
frames at each.

```bash
python summer_school/collect_orientation_data.py
```

Configuration constants at the top of the file:

| Constant | Default | Meaning |
|----------|---------|---------|
| `AXIS_START_DEG` / `AXIS_END_DEG` | `0.0` / `180.0` | azimuth sweep range (inclusive) |
| `AXIS_STEP_DEG` | `30.0` | azimuth step |
| `ANGLE_MIN_DEG` / `ANGLE_MAX_DEG` | `-10.0` / `10.0` | tilt range |
| `ANGLE_STEP_DEG` | `2.0` | tilt step |
| `BASE_Z_UM` | `0.0` | constant defocus applied during the whole sweep (µm) |
| `RETURN_HOME_BETWEEN_AXES` | `True` | return home between azimuth groups to avoid large jumps |
| `FRAMES_PER_POSE` | `1` | frames captured at each orientation |
| `SETTLE_S` | `0.5` | pause after each move before capturing (s) |

Flow: init SmarPod → set pivot at tip → prompt you to focus → for each `axis`, for each
`angle`, convert to `(dRx, dRy)`, check reachability, move, and capture labelled frames →
return home → save. Poses reported unreachable by the controller are skipped, not forced.

---

## 6. Output layout

Each run creates a fresh timestamped directory (never overwrites):

```
distance_data_<YYYY-MM-DD_HH-MM-SS>/
├── images/
│   ├── dist_0000_000um.png
│   ├── dist_0001_005um.png
│   └── ...
└── labels.json

orientation_data_<YYYY-MM-DD_HH-MM-SS>/
├── images/
│   ├── orient_0000_ax000_an-10.png
│   ├── orient_0001_ax000_an-08.png
│   └── ...
└── labels.json
```

`labels.json` holds run metadata plus one record per captured frame:

```json
{
    "metadata": {
        "type": "distance",
        "z_step_um": 5.0,
        "z_max_um": 200.0,
        "z_direction": -1,
        "frames_per_step": 1,
        "probe_tip_z_m": 0.0374
    },
    "records": [
        {
            "file": "images/dist_0000_000um.png",
            "distance_um": 0.0,
            "z_offset_um": 0,
            "pose": "0.0,0.0,0.0,0.0,0.0,0.0"
        }
    ]
}
```

Orientation records instead carry `axis_deg`, `angle_deg`, `dRx_deg`, `dRy_deg`, and
`base_z_um`. The `pose` string is `x,y,z,rx,ry,rz` (metres and degrees) as commanded.

Output directories are git-ignored (`distance_data_*/`, `orientation_data_*/`).

---

## 7. Safety

- **Every run moves the positioner.** Confirm clearance before starting.
- Press **Ctrl-C** to stop early: the script saves the data collected so far, returns the
  probe home, and closes the device in its `finally` block.
- Do a first pass with a coarse step / small range to confirm the capture region, pivot,
  and focus are correct before collecting a full dataset.

---

## 8. Building a dataset

- Run repeatedly on different samples and re-focus each time; keep each run's directory
  and merge the `labels.json` files at training time.
- Set `FRAMES_PER_STEP` / `FRAMES_PER_POSE` > 1 to average sensor noise per pose.
- Use `BASE_Z_UM` in the orientation sweep to also cover orientations captured slightly
  out of focus, if your model needs that robustness.

---

## 9. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Black or misaligned images | Wrong `PCLE_VIEW` in `common/capture.py`; re-find it with `tools/test.py` |
| Tip drifts while tilting | Wrong `PROBE_TIP_Z_M`; re-calibrate with `tools/robot_test.py` |
| Many "skip unreachable pose" lines | Tilt range too large for the pivot; reduce `ANGLE_MAX_DEG` or the pivot height |
| `incompatible python api and library version` at startup | SmarPod Python API and shared library major versions differ; reinstall matching SDK |
| `ModuleNotFoundError: smaract` | SmarAct SDK not installed in the active Python environment |

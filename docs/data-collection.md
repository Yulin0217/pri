# Data collection

Use the [installation and control-computer checklist](portability.md) first.
These commands move the positioner and capture the configured visible pCLE view.
They do not need an inference server. Changing the display, probe mounting,
pivot, or sample requires checking the corresponding configuration/reference.

## Distance groups

```bash
smarpod-pcle --config config/local.toml collect-distance
```

The command initializes the controller and sets the configured probe-tip pivot.
Before each group, bring the probe into best focus and press Enter. The actual
controller pose becomes that group's zero-distance reference. The workflow scans
along Z while retaining the reference X, Y and rotations, then returns to that
reference. Refocus on another sample/position and start another group, or enter
`q` to finish. Cleanup stops and closes; it does not retract or move to origin.

Scan constants live in
[`src/smarpod_pcle/data_collection/distance_sweep.py`](../src/smarpod_pcle/data_collection/distance_sweep.py):

| Constant | Default | Meaning |
| --- | --- | --- |
| `Z_STEP_UM` | `10.0` | Defocus increment in micrometres |
| `Z_MAX_UM` | `200.0` | Largest permitted defocus |
| `Z_DIRECTION` | `-1` | Direction of travel relative to focus |
| `FRAMES_PER_STEP` | `1` | Captures at each pose |
| `SETTLE_S` | `0.5` | Pause after a move |

Steps never exceed the maximum; if the endpoint is not on the grid, the last
sample is below it. Unreachable poses are skipped. Negative Z was the original
setup's away-from-sample convention; verify it on the assembled hardware.
`distance_um` is a nonnegative dataset label, whereas `z_offset_um` includes the
configured direction. Neither is automatically a signed servo correction.

Output example:

```text
runs/distance_data_<timestamp>/
  images/g00_dist_0000_000um.png
  images/g00_dist_0001_010um.png
  labels.json
```

The JSON contains `metadata` and `records`. Metadata includes scan settings,
pivot, group count and `reference_poses` (one actual pose per started group).
An image record looks like:

```json
{
  "file": "images/g00_dist_0001_010um.png",
  "group": 0,
  "distance_um": 10.0,
  "z_offset_um": -10.0,
  "pose": "0.0,0.0,-1e-05,0.0,0.0,0.0"
}
```

`pose` is the commanded `x,y,z,rx,ry,rz`, in metres and degrees. Paths are relative
to the run directory. Labels are appended only after an image is saved.

## Orientation grid

```bash
smarpod-pcle --config config/local.toml collect-orientation
```

After initialization, manually focus and press Enter. This measured pose is the
reference for the whole run. X/Y remain at the reference, Z is offset by
`-abs(BASE_Z_UM)` micrometres (converted to metres for the SDK), and the calculated
tilt components are added to the reference X/Y rotations. Reference Z rotation
is retained.

Scan constants live in
[`src/smarpod_pcle/data_collection/orientation_sweep.py`](../src/smarpod_pcle/data_collection/orientation_sweep.py):

| Constant | Default |
| --- | --- |
| `AXIS_START_DEG`, `AXIS_END_DEG`, `AXIS_STEP_DEG` | `0`, `180`, `30` |
| `ANGLE_MIN_DEG`, `ANGLE_MAX_DEG`, `ANGLE_STEP_DEG` | `-10`, `10`, `2` |
| `BASE_Z_UM` | `0.0` |
| `FRAMES_PER_POSE`, `SETTLE_S` | `1`, `0.5` |
| `RETURN_HOME_BETWEEN_AXES` | `True` (historical name; returns to focus reference) |

`axis` is the tilt-axis azimuth: 0° corresponds to X and 90° to Y. Signed `angle`
is projected into X/Y components using the original `compute_dRx_dRy` helper.
This preserves the legacy small-angle convention; additive Euler components are
not exact general 3D rotation composition. Use a near-aligned reference and
validate the actual tilt/pivot behavior before treating labels as ground truth.
The signed-angle/axis endpoints contain some equivalent orientations.

Each `orientation_data_<timestamp>/` directory holds `images/` and `labels.json`.
Records contain `file`, `axis_deg`, `angle_deg`, `dRx_deg`, `dRy_deg`, `base_z_um`,
and the commanded `pose`. Metadata records `reference_pose` and
`rotation_convention = "additive_controller_euler_offsets"`, plus scan settings.
A successful run returns to its focus reference. A failed/interrupted run does
not add a reference-return move.

## Slow spiral and legacy grid

`collect-spiral` is the old `summer_school/data_collection.py`: a slow open-loop
XY spiral, with raw/mosaic images and `positions.txt`. Its recipe and optional
`USE_SERVER` switch are in
[`data_collection/spiral_capture.py`](../src/smarpod_pcle/data_collection/spiral_capture.py);
server use is disabled by default. It is distinct from the two labelled
collectors above and does not stitch a mosaic itself.

`grid-scan` is the older 21×21 XY scan spanning ±1 mm with 0.1 mm pitch. It retains
41 repeated captures per XY point. The legacy `n` filename suffix ranges from
0 to 400 but **does not command Z movement**; do not train a distance model using
that suffix as a physical label. Its trajectory records now use distinct indices.
The implementation is
[`scan_experiments/xy_grid_capture.py`](../src/smarpod_pcle/scan_experiments/xy_grid_capture.py).
See [the entry-point map](project-layout.md) for all retained script names.

## Interruptions and dataset handling

Ctrl-C or input EOF stops collection and attempts to save completed records.
Normal returns to a reference are part of the workflow; error cleanup only
stops and closes the controller. A disk write failure cannot guarantee a complete
label file, but cleanup still attempts to close the hardware. Sudden process
termination or loss of power can lose in-memory labels. Keep adequate disk space
and inspect saved counts after every run.

Repeat runs across samples, recording calibration and reference conventions.
Keep each run directory intact and combine records at training time. Increasing
frames per pose collects repeated observations; it does not itself average them.

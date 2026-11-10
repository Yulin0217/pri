# Project layout and entry points

`mosaic-scan` uses `mosaicking/scan_patterns.py` and the shared mosaic runner.
See [alternative scan usage](mosaic-scans.md).
Independent `mosaic-serpentine`, `mosaic-raster`, and `mosaic-rings` commands use
`mosaicking/{serpentine,raster,rings}_mosaic.py`. Standalone adapters are
`mosaicking/mosaic_{serpentine,raster,rings}.py` at the repository root.

The maintained Python package is [`src/smarpod_pcle/`](../src/smarpod_pcle/).
Choose files by their responsibility: complete server-connected applications,
data collection, image mosaicking, interactive tools, scan experiments, or
vendor examples. The [root README](../README.md#repository-structure) lists the
canonical files and their responsibilities.

## Where changes belong

- `applications/` contains the visual-servo client and the local spiral demo that
  exchanges images with a server. These orchestrate capture, network operations,
  and, where applicable, motion.
- `data_collection/` contains workflows that produce images and labels or pose
  logs. `collection_helpers.py` shares range validation, probe setup, and label
  persistence between the distance and orientation collectors.
- `mosaicking/` contains image placement and scan orchestration.
  `mosaic_canvas.py` handles trajectory generation and blending without hardware.
  `scan_runner.py` manages the common capture/motion/save lifecycle.
  `direct_mosaic.py` selects commanded-position placement;
  `regression_mosaic.py` supplies model displacements and permanent fallback.
- `interactive_tools/` contains operator-driven screenshot preview, Z jogging,
  and probe-pivot checks.
- `scan_experiments/` preserves the laboratory XY grid and cross-scan recipes.
  Their descriptive names make clear that neither is a cone-rotation workflow
  or a distance-labelled Z sweep.
- `sdk_examples/` preserves the vendor-derived pose-sequence and controller-setup
  examples, including their original copyright notices. These are explicit
  hardware commands, not installation tests.

Machine settings belong in `config/local.toml`. Scan ranges, delays, and other
recipe constants live in the relevant workflow module. With the editable
installation, source changes are used on the next run; do not edit the historical
root wrappers to change behavior.

The shared modules separate concerns:

| Module | Responsibility |
| --- | --- |
| [cli.py](../src/smarpod_pcle/cli.py) | Parse commands/options, load settings, then import the selected workflow |
| [doctor.py](../src/smarpod_pcle/doctor.py) | Check packages and output access; perform SDK/capture/TCP checks only when requested |
| [config.py](../src/smarpod_pcle/config.py) | Load and validate machine-specific TOML settings |
| [robot_control.py](../src/smarpod_pcle/robot_control.py) | Load the vendor SDK, initialize a handle, check movement targets, and stop/close |
| [geometry.py](../src/smarpod_pcle/geometry.py) | Convert tilt components and format poses without loading the SDK |
| [screen_capture.py](../src/smarpod_pcle/screen_capture.py) | Capture configured pCLE and mosaic screen rectangles |
| [tcp_protocol.py](../src/smarpod_pcle/tcp_protocol.py) | Frame trusted pickle messages, read complete payloads, and JPEG-encode frames |
| [run_output.py](../src/smarpod_pcle/run_output.py) | Create unique output directories and check image writes |

For a typical command, `cli.py` validates configuration and dispatches to a
workflow. The workflow calls the shared modules for each operation. Importing a
workflow does not initialize the robot; hardware operations begin only when its
explicit entry point runs. See [development.md](development.md) for lifecycle and
testing boundaries.

## Commands and historical script paths

Install the project first, then use the primary command names in the
[README command guide](../README.md#commands). That guide is the reference for
CLI syntax, options, aliases, and each command's hardware/server requirements.

The original root-level scripts remain runnable compatibility adapters. They
delegate to the installed package and contain no maintained workflow logic:

| Primary command | Canonical implementation under `src/smarpod_pcle/` | Retained root script |
| --- | --- | --- |
| `servo-client` | [applications/visual_servo_client.py](../src/smarpod_pcle/applications/visual_servo_client.py) | [apps/client.py](../apps/client.py) |
| `spiral-demo` | [applications/spiral_stream_demo.py](../src/smarpod_pcle/applications/spiral_stream_demo.py) | [apps/demo.py](../apps/demo.py) |
| `collect-distance` | [data_collection/distance_sweep.py](../src/smarpod_pcle/data_collection/distance_sweep.py) | [summer_school/collect_distance_data.py](../summer_school/collect_distance_data.py) |
| `collect-orientation` | [data_collection/orientation_sweep.py](../src/smarpod_pcle/data_collection/orientation_sweep.py) | [summer_school/collect_orientation_data.py](../summer_school/collect_orientation_data.py) |
| `collect-spiral` | [data_collection/spiral_capture.py](../src/smarpod_pcle/data_collection/spiral_capture.py) | [summer_school/data_collection.py](../summer_school/data_collection.py) |
| `mosaic-direct` | [mosaicking/direct_mosaic.py](../src/smarpod_pcle/mosaicking/direct_mosaic.py) | [mosaicking/mosaic_direct.py](../mosaicking/mosaic_direct.py) |
| `mosaic-regression` | [mosaicking/regression_mosaic.py](../src/smarpod_pcle/mosaicking/regression_mosaic.py) | [mosaicking/mosaic_regression.py](../mosaicking/mosaic_regression.py) |
| `capture-region` | [interactive_tools/screen_region_preview.py](../src/smarpod_pcle/interactive_tools/screen_region_preview.py) | [tools/test.py](../tools/test.py) |
| `jog-z` | [interactive_tools/z_axis_jog.py](../src/smarpod_pcle/interactive_tools/z_axis_jog.py) | [tools/manual_z_step_control.py](../tools/manual_z_step_control.py) |
| `pivot-check` | [interactive_tools/probe_pivot_check.py](../src/smarpod_pcle/interactive_tools/probe_pivot_check.py) | [tools/robot_test.py](../tools/robot_test.py) |
| `grid-scan` | [scan_experiments/xy_grid_capture.py](../src/smarpod_pcle/scan_experiments/xy_grid_capture.py) | [experiments/data_collection.py](../experiments/data_collection.py) |
| `cross-scan` | [scan_experiments/xy_cross_scan.py](../src/smarpod_pcle/scan_experiments/xy_cross_scan.py) | [experiments/cone_rotation.py](../experiments/cone_rotation.py) |
| `sdk-pose-sequence` | [sdk_examples/pose_sequence.py](../src/smarpod_pcle/sdk_examples/pose_sequence.py) | [examples/example1.py](../examples/example1.py) |
| `configure-controller` | [sdk_examples/configure_controller.py](../src/smarpod_pcle/sdk_examples/configure_controller.py) | [examples/example2.py](../examples/example2.py) |

For example, `python apps/client.py --mode 2` still selects streaming-only mode.
Select global configuration through the primary CLI or `SMARPOD_PCLE_CONFIG`
when using an old script path.

## Python import migration

Earlier internal package paths such as `smarpod_pcle.apps.client`,
`smarpod_pcle.collection.distance`, and `smarpod_pcle.hardware` were renamed.
They are not retained as alternate package trees. Update direct imports to the
canonical modules listed above. For example:

```python
from smarpod_pcle.geometry import compute_dRx_dRy
from smarpod_pcle.robot_control import move_checked
from smarpod_pcle.mosaicking.mosaic_canvas import MosaicCanvas
```

The root compatibility modules below still re-export maintained helpers when
used from the checkout. They do not recreate every historical global variable
or establish the old script implementation as a stable library API:

| Root compatibility module | Canonical module |
| --- | --- |
| `common/utils_client.py` | `smarpod_pcle.robot_control` |
| `common/capture.py` | `smarpod_pcle.screen_capture` |
| `common/net.py` | `smarpod_pcle.tcp_protocol` |
| `mosaicking/mosaic_core.py` | `smarpod_pcle.mosaicking.mosaic_canvas` |
| `summer_school/collection_utils.py` | `smarpod_pcle.data_collection.collection_helpers` |

A wheel contains the canonical package; the historical root folders belong to
the repository checkout. Use installed CLI commands and canonical imports when
deploying without the source checkout.

Renaming does not validate a hardware workflow. Retain the setup and geometry
caveats in the [README](../README.md#configuration) and complete the separate
[control-computer checks](portability.md) before moving the positioner.

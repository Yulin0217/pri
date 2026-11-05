# Running on another computer

This repository contains the **client and robot-control code**, not the SmarAct
SDK, pCLE acquisition software, inference server, or trained model weights.
Copying the repository or creating a conda environment does not install those
external components.

## Development computer versus control computer

The current development computer is an Apple Silicon Mac (`arm64`), and is not
the robot-control computer. It is used for editing, package installation,
offline tests, configuration checks, and image-processing development without a
connected robot. Hardware movement has not been validated on this computer.

SmarAct's public SMARPOD documentation lists its C++ and Python SDKs for
**Windows and Linux**. It does not establish macOS or Apple Silicon support for
the `smaract.smarpod` API used here. Choose a control computer supported by the
SDK supplied with your hardware; obtain confirmation from SmarAct before planning
native Mac control. The vendor also supplies software and SDK documentation with
the system. [SmarAct SMARPOD: Controller and Software](https://www.smaract.com/en/smarpod)

The exact supported OS releases, CPU architecture, Python versions, controller
firmware, and driver installation procedure must come from **your SDK release's
documentation**. This project uses Python 3.12 as its development environment;
that is not a claim that every SmarAct SDK supports Python 3.12. A CPU-compatible
Python environment cannot substitute for a missing native controller library.

## 1. Install the Python project

Install conda on the destination computer, clone this repository, check out the
`yulin` branch, and run the following from the repository root:

```bash
conda env create -f environment.yml
conda activate smarpod-pcle
smarpod-pcle --help
```

The environment file installs the project and development tools. For a non-conda
installation, use the [README quick start](../README.md#quick-start-development-without-a-robot).
When installing vendor bindings, use the activated environment's interpreter so
the project and vendor API run in the same Python environment.

Recreate the environment on each OS instead of copying a conda directory between
computers. Python wheels and native libraries are platform-specific. The
environment file describes the intended dependencies; record exact installed
versions alongside any experimental results that need to be reproduced.

## 2. Create a machine-specific configuration

Copy [config/example.toml](../config/example.toml) to `config/local.toml`, then
edit the copy. Keep the example as a reference, and keep local machine settings
out of version control.

- `robot.model` and `robot.locator`: the actual SmarPod model code and controller
  connection. `10001` and `usb:ix:0` are inherited laboratory defaults, not
  discovery results for a new computer.
- `robot.speed_m_s`, `robot.max_frequency_hz`, and `robot.probe_tip_z_m`: movement
  settings and the calibrated platform-to-probe-tip pivot distance.
- `server.host`, `server.port`, and `server.timeout_s`: the compatible inference
  service, for commands that use one. The default is `127.0.0.1`; the historical
  laboratory address mentioned in the example is not a public service.
- `capture.pcle_view` and `capture.mosaic_view`: screen rectangles in pixels, with
  `top`, `left`, `width`, and `height`. These must match the destination display.
- `output_dir`: a writable location with enough space for captured images and
  logs. Prefer a deliberate data directory when running outside the checkout.
- `mosaic.meters_per_pixel`, `mosaic.sign_x`, `mosaic.sign_y`, `mosaic.blend`, and
  `mosaic.regression_in_micrometers`: image-placement calibration and the
  regression server's displacement units. Calibrate these for the actual optics.

Relative `output_dir` paths are resolved against the configuration file's
directory. Importing project modules or asking for CLI help does not initialize
hardware. Existing script paths are compatibility wrappers around the installed
package; use the CLI to make the selected configuration explicit.
The [layout and migration guide](project-layout.md) maps those paths to the
current implementations and lists the supported command aliases.

Run a check that does not open the robot, capture the screen, or contact a server:

```bash
smarpod-pcle --config config/local.toml doctor
```

This checks the Python packages, configuration, and output location. Passing it
means the software prerequisites checked by this command are available; it does
not prove that a controller or inference model works.

## 3. Install the vendor software on the control computer

Use the SmarAct distribution supplied for the specific controller and SmarPod.
Follow its installation instructions for the native runtime, USB driver or
network access, and Python bindings. Install or expose `smaract.smarpod` inside
the activated `smarpod-pcle` environment using the method documented by that SDK.
There is no universal wheel path or pip command in this repository because the
vendor distribution is not included.

Confirm the following before running a movement command:

1. The vendor GUI can communicate with the intended controller.
2. The controller has the correct model configuration and firmware for the
   attached positioner.
3. The native library's platform and architecture match the interpreter.
4. The Python API and loaded native library have matching major versions.
5. The configured locator identifies the intended controller. A USB index can
   change when devices are added or reconnected.

Check SDK loading and major-version compatibility without opening a controller:

```bash
smarpod-pcle --config config/local.toml doctor --sdk
```

`--sdk` imports the vendor API and queries its library version. It does not call
`Open`, calibrate sensors, reference the axes, or move the robot. A successful
result does not verify device detection or movement.

`configure-controller` is a separate hardware setup command that writes the
controller's persistent configuration and then calibrates the robot. It is not a
routine dependency check and is not required merely because the client computer
has changed. Follow the SDK guidance for when reconfiguration is necessary.

## 4. Set up the pCLE display and capture

The project captures pixels from the visible pCLE viewer. It does not acquire
images directly from a camera driver. Install the acquisition/viewer software
and its hardware drivers, connect the pCLE system, and make its live view visible
on the same desktop session that runs this client.

MSS supports GNU/Linux, macOS, and Windows, independently of the robot SDK's
platform support. [MSS supported platforms](https://python-mss.readthedocs.io/latest/support.html)

On Linux, MSS documents X11 display selection through `DISPLAY` and X11 capture
backends. Use a working X11 desktop for this workflow. Native Wayland capture is
not established by those documented backends; verify the actual viewer capture
before adopting another session type. A headless shell by itself does not provide
the pCLE viewer desktop. [MSS Linux display and backends](https://python-mss.readthedocs.io/latest/usage.html#gnu-linux)

On macOS, grant screen-recording access to the application that launches the
capture process when requested. Review it under **System Settings → Privacy &
Security → Screen & System Audio Recording**. This enables screenshot testing;
it does not add SmarPod SDK support. [Apple screen-recording permissions](https://support.apple.com/en-gb/guide/mac-help/mchl592e5686/mac)

Use the capture tool to find the new rectangles, then update `config/local.toml`:

```bash
smarpod-pcle --config config/local.toml capture-region
smarpod-pcle --config config/local.toml doctor --capture
```

`--capture` requests the pCLE screenshot and prints its shape; it does not display
or save it, or check the mosaic rectangle. Use `capture-region` to visually
inspect both rectangles when the intended viewer is visible. Check that each
image contains the full intended view and excludes borders,
menus, or other windows. Repeat this after changing monitor resolution, display
scaling, window placement, or remote-desktop configuration. The capture-region
preview uses OpenCV GUI windows and needs a graphical session.

## 5. Provide the inference service when needed

`servo-client`, `spiral-demo`, and `mosaic-regression` use a remote service;
`collect-spiral` can optionally use one. The service implementation and weights
must be obtained separately. Match the request/response format in [protocol.md](protocol.md),
including the distinction between servo corrections and mosaic displacements.
Allow the configured TCP port through the appropriate host/network firewall.

```bash
smarpod-pcle --config config/local.toml doctor --server
```

`--server` opens and closes a TCP connection only. It sends no image, does not
unpickle a reply, and does not validate inference semantics. Use an endpoint that
you control and trust, since the operational protocol uses pickle.

Distance/orientation collection, local spiral collection, and direct mosaicking
do not need the inference server in their local modes. The client does not need
CUDA or a GPU simply to send screenshots to a separate inference machine.

## 6. Commission the actual hardware separately

Before the first movement run on a new setup, verify the probe mounting, pivot,
axis directions, focus reference, and clearance over the intended scan. For
mosaicking, also calibrate the pixel scale and image/stage axis signs. A
controller's reachability check only establishes that the mechanism can reach a
pose; it does not detect contact with the sample or surroundings.

Initialization may reference the positioner when it is not already referenced.
Sensor calibration, referencing, normal movement, and returning home all require
physical clearance. Inspect the command's settings before launching it. Keep the
controller's physical stop procedure available while commissioning. On an error
or interruption, cleanup stops and closes the controller without adding an
automatic return-home move. Successful workflows can still contain explicit
home or reference-return moves as described in their command documentation.

The refactor's offline checks and tests do not validate real motion, microscope
calibration, collision avoidance, the external server, or real-time performance.
Those checks must be performed on the assembled system by its operator.

## Troubleshooting

- **`No module named smaract`:** install the vendor Python API into the activated
  environment; check `python -c "import sys; print(sys.executable)"`.
- **Native library load error:** follow the SDK's runtime/library-search-path
  instructions and verify OS, architecture, dependent libraries, and versions.
  Copying only the Python source is insufficient.
- **API/library major-version mismatch:** install matching components from the
  same supported vendor release.
- **Controller unavailable:** check its power, cable, USB driver or network
  connection, selected locator, and whether another application holds it open.
- **Black, incorrect, or failed capture:** verify the viewer is visible, capture
  permissions, active display session, and both configured rectangles.
- **TCP connection fails:** check the server process, host/port, routing, and
  firewall. A successful ping alone does not verify a listening TCP service.
- **Connection succeeds but commands fail:** verify server message keys, units,
  pickle compatibility, and timeout against [protocol.md](protocol.md).

Vendor and platform sources above were checked on 5 November 2026. The release
notes delivered with the actual SDK take precedence for its supported systems.

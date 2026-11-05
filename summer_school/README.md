# Summer School data collection

The maintained implementations now live in `src/smarpod_pcle/collection/`.
Install the project with the [root quick start](../README.md), then follow the
[complete English collection guide](../docs/data-collection.md).

```bash
smarpod-pcle collect-distance
smarpod-pcle collect-orientation
smarpod-pcle collect-spiral
```

The original script paths remain compatibility entry points after installation:

- `collect_distance_data.py`: distance groups with manual focus per group.
- `collect_orientation_data.py`: orientation offsets from the actual focused pose.
- `data_collection.py`: slow open-loop spiral, not the labelled distance collector.

Use `smarpod-pcle --config config/local.toml <command>` to select machine settings.
The collection guide documents the 10 µm default distance step, group filenames,
label schemas, calibration, and updated stop/cleanup behavior. Deployment on the
robot computer is covered in [portability.md](../docs/portability.md).

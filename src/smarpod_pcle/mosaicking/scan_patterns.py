"""Bounded XY scan paths in metres, independent of hardware and capture."""

import math

MAX_POINTS = 100_000


def build_trajectory(pattern, *, width_m=0.0016, height_m=0.0016,
                     radius_m=0.0008, spacing_m=0.0001):
    """Generate centered raster/serpentine grids or center-out closed rings.

    Spacing bounds grid pitch, ring pitch and sampled ring arc length.
    Raster return moves are subdivided and captured to retain local overlap.
    These geometric bounds do not guarantee optical overlap.
    """
    if pattern not in ("serpentine", "raster", "rings"):
        raise ValueError("Unknown scan pattern")
    if not all(math.isfinite(v) and v > 0
               for v in (width_m, height_m, radius_m, spacing_m)):
        raise ValueError("Scan dimensions and spacing must be positive and finite")
    points = []

    def append(point):
        if len(points) >= MAX_POINTS:
            raise ValueError("Scan exceeds 100000 waypoints; increase spacing")
        points.append(point)

    def segments(length):
        ratio = length / spacing_m
        if not math.isfinite(ratio) or ratio > MAX_POINTS:
            raise ValueError("Scan is too dense; increase spacing")
        nearest = round(ratio)
        if math.isclose(ratio, nearest, rel_tol=1e-12, abs_tol=1e-12):
            ratio = nearest
        return max(1, math.ceil(ratio))

    def connect(point):
        if points:
            x, y = points[-1]
            count = segments(math.hypot(point[0] - x, point[1] - y))
            for k in range(1, count):
                append((x + (point[0] - x) * k / count,
                        y + (point[1] - y) * k / count))
        append(point)

    if pattern == "rings":
        append((0.0, 0.0))
        nr = segments(radius_m)
        for ring in range(1, nr + 1):
            radius = radius_m * ring / nr
            count = max(3, segments(2 * math.pi * radius))
            connect((radius, 0.0))
            for k in range(1, count):
                angle = 2 * math.pi * k / count
                append((radius * math.cos(angle), radius * math.sin(angle)))
            append((radius, 0.0))
    else:
        nx, ny = segments(width_m), segments(height_m)
        if (nx + 1) * (ny + 1) > MAX_POINTS:
            raise ValueError("Scan exceeds 100000 waypoints; increase spacing")
        for row in range(ny + 1):
            columns = range(nx + 1)
            if pattern == "serpentine" and row % 2:
                columns = reversed(columns)
            for col in columns:
                connect((-width_m / 2 + width_m * col / nx,
                         -height_m / 2 + height_m * row / ny))
    return points


def main(*, pattern="serpentine", width_um=1600, height_um=1600,
         radius_um=800, spacing_um=100, regression=False, dry_run=False):
    """Run an alternative path through the existing mosaic lifecycle."""
    trajectory = build_trajectory(pattern, width_m=width_um / 1e6,
                                  height_m=height_um / 1e6,
                                  radius_m=radius_um / 1e6,
                                  spacing_m=spacing_um / 1e6)
    metadata = dict(pattern=pattern, width_um=width_um, height_um=height_um,
                    radius_um=radius_um, spacing_um=spacing_um)
    if dry_run:
        import json
        print(json.dumps({"scan": metadata, "waypoints_m": trajectory}, indent=2))
        return
    from .scan_runner import run_scan
    run_scan(regression=regression, trajectory=trajectory, scan_metadata=metadata)

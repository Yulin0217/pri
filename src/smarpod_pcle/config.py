"""Validated, machine-local TOML configuration, loaded before any application."""

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
import math
import os
import tomllib


@dataclass(frozen=True)
class RobotSettings:
    model: int = 10001
    locator: str = "usb:ix:0"
    speed_m_s: float = 0.003
    max_frequency_hz: int = 18500
    probe_tip_z_m: float = 0.0374


@dataclass(frozen=True)
class ServerSettings:
    host: str = "127.0.0.1"
    port: int = 12334
    timeout_s: float = 5.0


@dataclass(frozen=True)
class CaptureSettings:
    pcle_view: dict = field(default_factory=lambda: dict(top=45, left=1118, width=350, height=350))
    mosaic_view: dict = field(default_factory=lambda: dict(top=420, left=1050, width=600, height=600))


@dataclass(frozen=True)
class MosaicSettings:
    meters_per_pixel: float = 1e-6
    sign_x: int = 1
    sign_y: int = 1
    blend: str = "average"
    regression_in_micrometers: bool = False


@dataclass(frozen=True)
class Settings:
    robot: RobotSettings = field(default_factory=RobotSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    capture: CaptureSettings = field(default_factory=CaptureSettings)
    mosaic: MosaicSettings = field(default_factory=MosaicSettings)
    output_dir: str = "runs"

    def as_dict(self):
        return asdict(self)


def _number(value, name, *, positive=False, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if integer and not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")


def _nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def validate(settings):
    r, s, c, m = settings.robot, settings.server, settings.capture, settings.mosaic
    _number(r.model, "robot.model", positive=True, integer=True)
    _nonempty(r.locator, "robot.locator")
    _number(r.speed_m_s, "robot.speed_m_s", positive=True)
    _number(r.max_frequency_hz, "robot.max_frequency_hz", positive=True, integer=True)
    _number(r.probe_tip_z_m, "robot.probe_tip_z_m")
    _nonempty(s.host, "server.host")
    _number(s.port, "server.port", positive=True, integer=True)
    if s.port > 65535:
        raise ValueError("server.port must be <= 65535")
    _number(s.timeout_s, "server.timeout_s", positive=True)
    for name in ("pcle_view", "mosaic_view"):
        rect = getattr(c, name)
        if not isinstance(rect, dict) or set(rect) != {"top", "left", "width", "height"}:
            raise ValueError(f"capture.{name} needs top, left, width and height")
        for key, value in rect.items():
            _number(value, f"capture.{name}.{key}", integer=True, positive=key in ("width", "height"))
    _number(m.meters_per_pixel, "mosaic.meters_per_pixel", positive=True)
    for name in ("sign_x", "sign_y"):
        value = getattr(m, name)
        if type(value) is not int or value not in (-1, 1):
            raise ValueError(f"mosaic.{name} must be -1 or 1")
    if m.blend not in ("average", "max", "overwrite"):
        raise ValueError("mosaic.blend must be average, max or overwrite")
    if type(m.regression_in_micrometers) is not bool:
        raise ValueError("mosaic.regression_in_micrometers must be true or false")
    _nonempty(settings.output_dir, "output_dir")
    return settings


def load_settings(path=None):
    """Explicit path > SMARPOD_PCLE_CONFIG > config/local.toml in cwd > defaults."""
    path = path or os.environ.get("SMARPOD_PCLE_CONFIG")
    if path is None and Path("config/local.toml").is_file():
        path = "config/local.toml"
    if path is None:
        return validate(Settings())
    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    unknown = data.keys() - {f.name for f in fields(Settings)}
    # Reject misspellings instead of silently applying a default to robot settings.
    if unknown:
        raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
    values = {}
    for name, cls in (("robot", RobotSettings), ("server", ServerSettings),
                      ("capture", CaptureSettings), ("mosaic", MosaicSettings)):
        section = data.get(name, {})
        if not isinstance(section, dict):
            raise ValueError(f"{name} must be a TOML table")
        unknown = section.keys() - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Unknown {name} settings: {', '.join(sorted(unknown))}")
        values[name] = cls(**section)
    output = data.get("output_dir", "../runs")
    _nonempty(output, "output_dir")
    output = Path(output).expanduser()
    if not output.is_absolute():
        # A saved machine configuration must select the same data location from any cwd.
        output = config_path.parent / output
    values["output_dir"] = str(output.resolve())
    return validate(Settings(**values))


_settings = None


def configure(path=None):
    global _settings
    _settings = load_settings(path)
    return _settings


def get_settings():
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings

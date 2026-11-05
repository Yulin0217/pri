"""Run directories and checked image writes."""

from datetime import datetime
from pathlib import Path
from .config import get_settings


def create_run_dir(prefix, root=None):
    root = Path(root if root is not None else get_settings().output_dir).expanduser()
    path = root / f"{prefix}_{datetime.now():%Y-%m-%d_%H-%M-%S_%f}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def save_image(path, image):
    import cv2
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Could not write image: {path}")

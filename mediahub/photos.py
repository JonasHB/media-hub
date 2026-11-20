from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

PHOTO_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
MAX_PHOTOS = 5000


def scan_photos(folders: list[str]) -> tuple[list[str], list[str]]:
    photos: list[str] = []
    warnings: list[str] = []

    for folder in folders:
        root = Path(folder).expanduser()
        if not root.is_dir():
            warnings.append(f"fotomapp finns inte: {root}")
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue
            if path.suffix.lower() in PHOTO_SUFFIXES:
                photos.append(str(path.resolve()))

    photos = list(dict.fromkeys(photos))
    if len(photos) > MAX_PHOTOS:
        warnings.append(
            f"fler än {MAX_PHOTOS} foton hittades, använder de första {MAX_PHOTOS}"
        )
        photos = photos[:MAX_PHOTOS]

    return photos, warnings

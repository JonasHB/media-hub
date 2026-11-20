from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Slot

log = logging.getLogger(__name__)

PHOTO_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
MAX_PHOTOS = 5000


class PhotoLibrary(QObject):
    def __init__(self, folders: list[str], parent=None):
        super().__init__(parent)
        self._folders = folders

    @Slot(result="QStringList")
    def refresh(self) -> list[str]:
        photos, warnings = scan_photos(self._folders)
        for warning in warnings:
            log.warning("%s", warning)
        return photos


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

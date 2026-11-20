from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

COVER_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")
COVER_NAME_SUFFIXES = ("", "-box2d", "-boxart", "-cover")
MEDIA_SUBDIRS = (
    "media/covers",
    "media/box2d",
    "media/boxart",
    "covers",
    "box2d",
    "boxart",
    "images",
)
ROM_PLACEHOLDER = "{rom}"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "rom"


def rom_title(path: Path) -> str:
    return path.stem.replace("_", " ").replace(".", " ").strip()


def find_cover(rom: Path, cover_dir: Path | None) -> str | None:
    directories = [rom.parent]
    directories.extend(rom.parent / subdir for subdir in MEDIA_SUBDIRS)
    if cover_dir is not None:
        directories.insert(0, cover_dir)

    candidates = [rom.with_suffix(suffix) for suffix in COVER_SUFFIXES]
    for directory in directories:
        for name_suffix in COVER_NAME_SUFFIXES:
            candidates.extend(
                directory / (rom.stem + name_suffix + suffix) for suffix in COVER_SUFFIXES
            )

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def expand_command(command: list[str], rom: Path) -> list[str]:
    return [arg.replace(ROM_PLACEHOLDER, str(rom)) for arg in command]


def scan_roms(rom_dirs: list[str], extensions: list[str]) -> list[Path]:
    suffixes = {ext.lower() for ext in extensions}
    found = []
    for directory in rom_dirs:
        root = Path(directory).expanduser()
        if not root.is_dir():
            log.warning("ROM directory does not exist: %s", root)
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in suffixes:
                found.append(path)
    return found


def iter_categories(categories):
    for category in categories:
        yield category
        yield from category.get("subcategories", [])


def report_missing_icons(config: dict) -> list[tuple[str, str, str]]:
    missing = []
    for category in iter_categories(config["categories"]):
        for item in category["items"]:
            icon = item["icon"]
            if icon is None or not Path(icon).is_file():
                missing.append((category["id"], item["id"], item["title"]))
    return missing


def apply_library(config: dict) -> list[str]:
    warnings: list[str] = []
    categories = {category["id"]: category for category in iter_categories(config["categories"])}
    used_ids = {
        item["id"] for category in categories.values() for item in category["items"]
    }

    for emulator in config.get("emulators", []):
        category = categories[emulator["category"]]
        cover_dir = Path(emulator["cover_dir"]).expanduser() if emulator["cover_dir"] else None
        roms = scan_roms(emulator["rom_dirs"], emulator["extensions"])

        if not roms:
            warnings.append(
                f"inga ROM-filer hittades för {emulator['title']} "
                f"({', '.join(emulator['rom_dirs'])})"
            )
            continue

        for rom in roms:
            base_id = f"rom-{slugify(rom.stem)}"
            item_id = base_id
            counter = 2
            while item_id in used_ids:
                item_id = f"{base_id}-{counter}"
                counter += 1
            used_ids.add(item_id)

            handover = dict(emulator["handover"])
            item = {
                "id": item_id,
                "title": rom_title(rom),
                "subtitle": emulator["title"],
                "icon": find_cover(rom, cover_dir),
                "launch": {
                    "command": expand_command(emulator["command"], rom)
                    + emulator["extra_args"],
                    "cwd": None,
                    "env": {},
                },
                "handover": handover,
            }
            category["items"].append(item)

    return warnings

"""Configuration loading and validation for Media Hub."""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any

from .library import ROM_PLACEHOLDER

CONFIG_VERSION = 1
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

HANDOVER_TYPES = {"window", "process", "none"}
CLOSE_STRATEGIES = {"graceful", "kill"}
GAMEPAD_BUTTONS = {
    "a",
    "b",
    "x",
    "y",
    "back",
    "start",
    "guide",
    "left_shoulder",
    "right_shoulder",
    "left_stick",
    "right_stick",
}
DEFAULT_EXIT_COMBO = ["left_shoulder", "right_shoulder"]
ICON_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")
COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class ConfigError(Exception):
    """Raised when a configuration file is invalid."""


class _Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def err(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}" if path else message)

    def object(self, value: Any, path: str) -> dict | None:
        if not isinstance(value, dict):
            self.err(path or "config", f"must be an object, got {_kind(value)}")
            return None
        return value

    def unknown_keys(self, value: dict, allowed: set[str], path: str) -> None:
        for key in value:
            if key in allowed:
                continue
            matches = difflib.get_close_matches(key, allowed, n=1)
            hint = f" (did you mean '{matches[0]}'?)" if matches else ""
            self.err(_join(path, key), f"unknown key{hint}")

    def string(self, value: Any, path: str, *, allow_empty: bool = False) -> str | None:
        if not isinstance(value, str):
            self.err(path, f"must be a string, got {_kind(value)}")
            return None
        if not allow_empty and not value.strip():
            self.err(path, "must not be empty")
            return None
        return value

    def boolean(self, value: Any, path: str) -> bool | None:
        if type(value) is not bool:
            self.err(path, f"must be true or false, got {_kind(value)}")
            return None
        return value

    def integer(self, value: Any, path: str, minimum: int, maximum: int) -> int | None:
        if type(value) is not int:
            self.err(path, f"must be an integer, got {_kind(value)}")
            return None
        if not minimum <= value <= maximum:
            self.err(path, f"must be between {minimum} and {maximum}, got {value}")
            return None
        return value

    def slug(self, value: Any, path: str, seen: set[str], what: str) -> str | None:
        text = self.string(value, path)
        if text is None:
            return None
        if not SLUG_RE.match(text):
            self.err(
                path,
                f"invalid {what} '{text}': use lowercase letters, digits, '-' and '_'",
            )
            return None
        if text in seen:
            self.err(path, f"duplicate {what} '{text}'")
            return None
        seen.add(text)
        return text


def _kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, list):
        return "an array"
    if isinstance(value, dict):
        return "an object"
    return type(value).__name__


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _find_auto_icon(base_dir: Path, item_id: str) -> str | None:
    icons_dir = base_dir / "icons"
    for suffix in ICON_SUFFIXES:
        candidate = icons_dir / f"{item_id}{suffix}"
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def _resolve(base: Path, value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return str(path.resolve())


def validate(raw: Any, base_dir: Path) -> dict:
    v = _Validator()
    cfg = v.object(raw, "")
    if cfg is None:
        raise ConfigError("\n".join(v.errors))

    v.unknown_keys(cfg, {"version", "settings", "categories", "emulators"}, "")

    version = cfg.get("version")
    if "version" not in cfg:
        v.err("version", f"missing required key (expected {CONFIG_VERSION})")
    elif v.integer(version, "version", 1, 1 << 30) != CONFIG_VERSION:
        v.err("version", f"unsupported version {version!r}, expected {CONFIG_VERSION}")

    settings = _validate_settings(v, cfg.get("settings", {}), "settings")
    categories = _validate_categories(v, cfg.get("categories"), base_dir)
    category_ids = {category["id"] for category in categories}
    emulators = _validate_emulators(v, cfg.get("emulators"), base_dir, category_ids)

    if v.errors:
        raise ConfigError("\n".join(v.errors))

    return {
        "version": CONFIG_VERSION,
        "settings": settings,
        "categories": categories,
        "emulators": emulators,
    }


def _validate_settings(v: _Validator, value: Any, path: str) -> dict:
    obj = v.object(value, path)
    if obj is None:
        return {"fps": 60, "animations": True}

    v.unknown_keys(obj, {"fps", "animations", "language", "exit_combo"}, path)

    fps = obj.get("fps", 60)
    if fps not in (30, 60):
        v.err(_join(path, "fps"), f"must be 30 or 60, got {fps!r}")

    animations = v.boolean(obj.get("animations", True), _join(path, "animations"))

    language = obj.get("language", "sv")
    if language not in ("sv", "en"):
        v.err(_join(path, "language"), "must be 'sv' or 'en'")

    exit_combo = _validate_exit_combo(v, obj.get("exit_combo"), _join(path, "exit_combo"))

    return {
        "fps": fps if fps in (30, 60) else 60,
        "animations": True if animations is None else animations,
        "language": language if language in ("sv", "en") else "sv",
        "exit_combo": exit_combo,
    }


def _validate_exit_combo(v: _Validator, value: Any, path: str) -> list[str]:
    if value is None:
        return list(DEFAULT_EXIT_COMBO)
    if not isinstance(value, list) or not value:
        v.err(path, "must be a non-empty array of gamepad button names")
        return list(DEFAULT_EXIT_COMBO)

    combo = []
    for index, name in enumerate(value):
        if not isinstance(name, str) or name not in GAMEPAD_BUTTONS:
            v.err(
                f"{path}[{index}]",
                f"unknown button {name!r}, use one of {', '.join(sorted(GAMEPAD_BUTTONS))}",
            )
            continue
        combo.append(name)
    return combo or list(DEFAULT_EXIT_COMBO)


def _validate_emulators(
    v: _Validator, value: Any, base_dir: Path, category_ids: set[str]
) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list):
        v.err("emulators", f"must be an array, got {_kind(value)}")
        return []

    seen: set[str] = set()
    emulators: list[dict] = []
    for index, raw_emulator in enumerate(value):
        path = f"emulators[{index}]"
        emulator = v.object(raw_emulator, path)
        if emulator is None:
            continue

        v.unknown_keys(
            emulator,
            {"id", "title", "command", "rom_dirs", "extensions", "category", "handover", "cover_dir", "extra_args"},
            path,
        )

        emulator_id = v.slug(emulator.get("id"), _join(path, "id"), seen, "emulator id")
        if "id" not in emulator:
            v.err(_join(path, "id"), "missing required key")
        title = v.string(emulator.get("title"), _join(path, "title"))

        command = _validate_rom_command(v, emulator.get("command"), f"{path}.command")

        rom_dirs: list[str] = []
        raw_dirs = emulator.get("rom_dirs")
        if not isinstance(raw_dirs, list) or not raw_dirs:
            v.err(_join(path, "rom_dirs"), "must be a non-empty array of directories")
        else:
            for dir_index, directory in enumerate(raw_dirs):
                dir_path = v.string(directory, f"{path}.rom_dirs[{dir_index}]")
                if dir_path is not None:
                    rom_dirs.append(_resolve(base_dir, dir_path))

        extensions: list[str] = []
        raw_extensions = emulator.get("extensions")
        if not isinstance(raw_extensions, list) or not raw_extensions:
            v.err(_join(path, "extensions"), "must be a non-empty array of file extensions")
        else:
            for ext_index, extension in enumerate(raw_extensions):
                ext_path = f"{path}.extensions[{ext_index}]"
                if not isinstance(extension, str) or not extension.startswith("."):
                    v.err(ext_path, "must be a string starting with '.', e.g. '.sfc'")
                    continue
                extensions.append(extension)

        category = emulator.get("category")
        if not isinstance(category, str) or category not in category_ids:
            v.err(
                _join(path, "category"),
                f"must reference an existing category id, got {category!r}",
            )

        handover = _validate_handover(v, emulator.get("handover"), f"{path}.handover")
        if handover is None:
            v.err(_join(path, "handover"), "required for emulators (use type 'window')")
        elif handover["type"] != "window":
            v.err(_join(path, "handover.type"), "emulators must use handover type 'window'")

        cover_dir = None
        if "cover_dir" in emulator:
            cover_value = v.string(emulator["cover_dir"], _join(path, "cover_dir"))
            if cover_value is not None:
                cover_dir = _resolve(base_dir, cover_value)

        extra_args: list[str] = []
        raw_extra = emulator.get("extra_args", [])
        if not isinstance(raw_extra, list):
            v.err(_join(path, "extra_args"), "must be an array of strings")
        else:
            for arg_index, arg in enumerate(raw_extra):
                if not isinstance(arg, str):
                    v.err(f"{path}.extra_args[{arg_index}]", f"must be a string, got {_kind(arg)}")
                else:
                    extra_args.append(arg)

        emulators.append(
            {
                "id": emulator_id or f"emulator-{index}",
                "title": title or f"Emulator {index + 1}",
                "command": command,
                "rom_dirs": rom_dirs,
                "extensions": extensions,
                "category": category if isinstance(category, str) else "",
                "handover": handover,
                "cover_dir": cover_dir,
                "extra_args": extra_args,
            }
        )
    return emulators


def _validate_rom_command(v: _Validator, value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not value:
        v.err(path, "must be a non-empty array of strings")
        return []
    command = []
    for index, arg in enumerate(value):
        if not isinstance(arg, str):
            v.err(f"{path}[{index}]", f"must be a string, got {_kind(arg)}")
            continue
        command.append(arg)
    if not any(ROM_PLACEHOLDER in arg for arg in command):
        v.err(path, f"must contain the {ROM_PLACEHOLDER} placeholder for the ROM path")
    return command


def _validate_categories(v: _Validator, value: Any, base_dir: Path) -> list[dict]:
    if not isinstance(value, list):
        v.err("categories", f"must be an array, got {_kind(value)}")
        return []
    if not value:
        v.err("categories", "must contain at least one category")
        return []

    seen_categories: set[str] = set()
    seen_items: set[str] = set()
    categories: list[dict] = []

    for index, raw_category in enumerate(value):
        path = f"categories[{index}]"
        category = v.object(raw_category, path)
        if category is None:
            continue

        v.unknown_keys(category, {"id", "title", "theme", "items"}, path)

        category_id = v.slug(
            category.get("id", f"category-{index}"), _join(path, "id"), seen_categories, "category id"
        )
        if "id" not in category:
            v.err(_join(path, "id"), "missing required key")
        title = v.string(category.get("title"), _join(path, "title"))
        theme = None
        if "theme" in category:
            theme_value = v.string(category["theme"], _join(path, "theme"))
            if theme_value is not None:
                if COLOR_RE.match(theme_value):
                    theme = theme_value
                else:
                    v.err(_join(path, "theme"), f"must be a colour like '#4d9dff', got {theme_value!r}")

        items = _validate_items(v, category.get("items"), f"{path}.items", base_dir, seen_items)
        categories.append(
            {
                "id": category_id or f"category-{index}",
                "title": title or f"Category {index + 1}",
                "theme": theme,
                "items": items,
            }
        )

    return categories


def _validate_items(
    v: _Validator, value: Any, path: str, base_dir: Path, seen_items: set[str]
) -> list[dict]:
    if not isinstance(value, list):
        v.err(path, f"must be an array, got {_kind(value)}")
        return []
    if not value:
        v.err(path, "must contain at least one item")
        return []

    items: list[dict] = []
    for index, raw_item in enumerate(value):
        item_path = f"{path}[{index}]"
        item = v.object(raw_item, item_path)
        if item is None:
            continue

        v.unknown_keys(item, {"id", "title", "subtitle", "icon", "launch", "handover"}, item_path)

        item_id = v.slug(item.get("id", f"item-{index}"), _join(item_path, "id"), seen_items, "item id")
        if "id" not in item:
            v.err(_join(item_path, "id"), "missing required key")

        title = v.string(item.get("title"), _join(item_path, "title"))
        subtitle = None
        if "subtitle" in item:
            subtitle = v.string(item["subtitle"], _join(item_path, "subtitle"), allow_empty=True)

        icon = None
        if "icon" in item:
            icon_value = v.string(item["icon"], _join(item_path, "icon"))
            if icon_value is not None:
                icon = _resolve(base_dir, icon_value)
        elif item_id is not None:
            icon = _find_auto_icon(base_dir, item_id)

        launch = _validate_launch(v, item.get("launch"), f"{item_path}.launch", base_dir)
        handover = _validate_handover(v, item.get("handover"), f"{item_path}.handover")

        items.append(
            {
                "id": item_id or f"item-{index}",
                "title": title or f"Item {index + 1}",
                "subtitle": subtitle,
                "icon": icon,
                "launch": launch,
                "handover": handover,
            }
        )

    return items


def _validate_launch(v: _Validator, value: Any, path: str, base_dir: Path) -> dict:
    launch = v.object(value, path)
    if launch is None:
        v.err(path, "missing required object with a 'command'")
        return {"command": [], "cwd": None, "env": {}}

    v.unknown_keys(launch, {"command", "cwd", "env"}, path)

    command = launch.get("command")
    if not isinstance(command, list) or not command:
        v.err(
            _join(path, "command"),
            "must be a non-empty array of strings "
            "(pass the program and each argument as separate array values)",
        )
        command = []
    else:
        for index, arg in enumerate(command):
            if not isinstance(arg, str):
                v.err(
                    f"{path}.command[{index}]",
                    f"must be a string, got {_kind(arg)} (pass arguments as separate array values)",
                )

    cwd = None
    if "cwd" in launch:
        cwd_value = v.string(launch["cwd"], _join(path, "cwd"))
        if cwd_value is not None:
            cwd = _resolve(base_dir, cwd_value)

    env_raw = launch.get("env", {})
    env: dict[str, str] = {}
    if not isinstance(env_raw, dict):
        v.err(_join(path, "env"), f"must be an object of string values, got {_kind(env_raw)}")
    else:
        for key, val in env_raw.items():
            if not isinstance(val, str):
                v.err(f"{path}.env.{key}", f"must be a string, got {_kind(val)}")
            else:
                env[key] = val

    return {"command": command, "cwd": cwd, "env": env}


def _validate_handover(v: _Validator, value: Any, path: str) -> dict | None:
    if value is None:
        return None

    handover = v.object(value, path)
    if handover is None:
        return None

    v.unknown_keys(
        handover,
        {"type", "window_class", "profile", "start_timeout_ms", "restore_focus", "close_strategy", "fullscreen"},
        path,
    )

    handover_type = handover.get("type", "process")
    if handover_type not in HANDOVER_TYPES:
        v.err(
            _join(path, "type"),
            f"must be one of {', '.join(sorted(HANDOVER_TYPES))}, got {handover_type!r}",
        )
        handover_type = "process"

    window_class = None
    if "window_class" in handover:
        window_class = v.string(handover["window_class"], _join(path, "window_class"))
    if handover_type == "window" and window_class is None:
        v.err(_join(path, "window_class"), "required when handover type is 'window'")

    profile = None
    if "profile" in handover:
        profile = v.string(handover["profile"], _join(path, "profile"))

    timeout = v.integer(
        handover.get("start_timeout_ms", 20000), _join(path, "start_timeout_ms"), 1000, 300000
    )
    restore_focus = v.boolean(handover.get("restore_focus", True), _join(path, "restore_focus"))

    close_strategy = handover.get("close_strategy", "graceful")
    if close_strategy not in CLOSE_STRATEGIES:
        v.err(
            _join(path, "close_strategy"),
            f"must be one of {', '.join(sorted(CLOSE_STRATEGIES))}, got {close_strategy!r}",
        )
        close_strategy = "graceful"

    fullscreen = v.boolean(handover.get("fullscreen", False), _join(path, "fullscreen"))

    return {
        "type": handover_type,
        "window_class": window_class,
        "profile": profile,
        "start_timeout_ms": 20000 if timeout is None else timeout,
        "restore_focus": True if restore_focus is None else restore_focus,
        "close_strategy": close_strategy,
        "fullscreen": False if fullscreen is None else fullscreen,
    }


def load_config(path: str | Path) -> dict:
    config_path = Path(path).expanduser()
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(str(config_path)) from None
    except OSError as exc:
        raise ConfigError(f"could not read {config_path}: {exc}") from exc

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from None

    return validate(raw, config_path.parent)


def find_item(config: dict, item_id: str) -> dict | None:
    for category in config["categories"]:
        for item in category["items"]:
            if item["id"] == item_id:
                return item
    return None

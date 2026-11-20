import pytest

from mediahub.config import ConfigError, validate
from mediahub.library import apply_library, slugify


def emulator(**overrides):
    base = {
        "id": "snes9x",
        "title": "Super Nintendo",
        "category": "games",
        "rom_dirs": ["roms"],
        "extensions": [".sfc", ".smc"],
        "command": ["snes9x", "{rom}"],
        "handover": {
            "type": "window",
            "window_class": "snes9x-gtk Snes9x-gtk",
        },
    }
    base.update(overrides)
    return base


def raw_config(**overrides):
    data = {
        "version": 1,
        "categories": [
            {"id": "games", "title": "Spel", "items": [
                {"id": "steam", "title": "Steam", "launch": {"command": ["steam"]}}
            ]}
        ],
        "emulators": [emulator()],
    }
    data.update(overrides)
    return data


def test_slugify():
    assert slugify("Super Mario All-Stars") == "super-mario-all-stars"
    assert slugify("Zelda: A Link to the Past") == "zelda-a-link-to-the-past"
    assert slugify("!!!") == "rom"


def test_scan_and_generate_items(tmp_path):
    roms = tmp_path / "roms"
    roms.mkdir()
    (roms / "Super Mario All-Stars.sfc").write_bytes(b"rom")
    (roms / "Zelda.smc").write_bytes(b"rom")
    (roms / "notes.txt").write_text("not a rom")
    (roms / "Zelda.png").write_bytes(b"cover")

    config = validate(raw_config(), tmp_path)
    warnings = apply_library(config)

    assert warnings == []
    items = config["categories"][0]["items"]
    assert [item["id"] for item in items] == ["steam", "rom-super-mario-all-stars", "rom-zelda"]
    mario = items[1]
    assert mario["title"] == "Super Mario All-Stars"
    assert mario["subtitle"] == "Super Nintendo"
    assert mario["icon"] is None
    assert mario["launch"]["command"] == ["snes9x", str(roms / "Super Mario All-Stars.sfc")]
    assert mario["handover"]["window_class"] == "snes9x-gtk Snes9x-gtk"
    zelda = items[2]
    assert zelda["icon"] == str((roms / "Zelda.png").resolve())


def test_cover_found_in_media_subfolders(tmp_path):
    roms = tmp_path / "roms"
    (roms / "media" / "covers").mkdir(parents=True)
    (roms / "Game.sfc").write_bytes(b"rom")
    (roms / "media" / "covers" / "Game.png").write_bytes(b"cover")
    config = validate(raw_config(emulators=[emulator(rom_dirs=["roms"])]), tmp_path)
    apply_library(config)
    assert config["categories"][0]["items"][1]["icon"].endswith("media/covers/Game.png")


def test_extra_args_appended(tmp_path):
    (tmp_path / "roms").mkdir()
    (tmp_path / "roms" / "Game.sfc").write_bytes(b"rom")
    config = validate(raw_config(emulators=[emulator(extra_args=["-fullscreen"])]), tmp_path)
    apply_library(config)
    command = config["categories"][0]["items"][1]["launch"]["command"]
    assert command == ["snes9x", str(tmp_path / "roms" / "Game.sfc"), "-fullscreen"]


def test_missing_rom_directory_warns(tmp_path):
    config = validate(raw_config(), tmp_path)
    warnings = apply_library(config)
    assert warnings and "inga ROM-filer" in warnings[0]
    assert len(config["categories"][0]["items"]) == 1


def test_duplicate_rom_titles_get_unique_ids(tmp_path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    (first / "Game.sfc").write_bytes(b"rom")
    (second / "Game.sfc").write_bytes(b"rom")
    config = validate(
        raw_config(emulators=[emulator(rom_dirs=["a", "b"])]), tmp_path
    )
    apply_library(config)
    ids = [item["id"] for item in config["categories"][0]["items"]]
    assert ids == ["steam", "rom-game", "rom-game-2"]


def test_command_requires_rom_placeholder(tmp_path):
    with pytest.raises(ConfigError, match=r"\{rom\}"):
        validate(raw_config(emulators=[emulator(command=["snes9x"])]), tmp_path)


def test_extension_must_start_with_dot(tmp_path):
    with pytest.raises(ConfigError, match="starting with"):
        validate(raw_config(emulators=[emulator(extensions=["sfc"])]), tmp_path)


def test_emulator_category_must_exist(tmp_path):
    with pytest.raises(ConfigError, match="existing category"):
        validate(raw_config(emulators=[emulator(category="nope")]), tmp_path)


def test_emulator_requires_window_handover(tmp_path):
    data = raw_config()
    data["emulators"][0]["handover"] = {"type": "process"}
    with pytest.raises(ConfigError, match="must use handover type 'window'"):
        validate(data, tmp_path)

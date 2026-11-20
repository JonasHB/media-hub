import json
from pathlib import Path

import pytest

from mediahub.config import ConfigError, find_item, load_config, validate

EXAMPLE = Path(__file__).resolve().parent.parent / "config" / "example.json"


def write_config(tmp_path: Path, data) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def minimal_config(**overrides):
    config = {
        "version": 1,
        "categories": [
            {
                "id": "streaming",
                "title": "Streaming",
                "items": [
                    {
                        "id": "youtube",
                        "title": "YouTube",
                        "launch": {"command": ["firefox", "https://youtube.com/"]},
                    }
                ],
            }
        ],
    }
    config.update(overrides)
    return config


def test_example_config_is_valid():
    config = load_config(EXAMPLE)
    assert [c["id"] for c in config["categories"]] == ["streaming", "games"]
    settings = dict(config["settings"])
    settings.pop("screensaver")
    assert settings == {
        "fps": 60,
        "animations": True,
        "language": "sv",
        "exit_combo": ["left_shoulder", "right_shoulder"],
    }
    screensaver = config["settings"]["screensaver"]
    assert screensaver["idle_seconds"] == 300
    assert screensaver["photo_seconds"] == 10
    assert screensaver["order"] == "random"
    assert len(screensaver["folders"]) == 1
    assert [e["id"] for e in config["emulators"]] == ["snes9x"]
    youtube = find_item(config, "youtube")
    assert youtube["handover"]["type"] == "window"
    assert youtube["handover"]["window_class"] == "Navigator firefox_firefox"
    assert youtube["icon"].endswith("/config/icons/youtube.png")
    assert Path(youtube["icon"]).is_absolute()


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.json")


def test_invalid_json_reports_position(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"version": 1,', encoding="utf-8")
    with pytest.raises(ConfigError, match="line 1"):
        load_config(path)


def test_unknown_key_suggests_close_match(tmp_path):
    data = minimal_config(settings={"animaton": True})
    with pytest.raises(ConfigError) as excinfo:
        load_config(write_config(tmp_path, data))
    assert "unknown key" in str(excinfo.value)
    assert "did you mean 'animations'" in str(excinfo.value)


def test_duplicate_item_id(tmp_path):
    data = minimal_config()
    data["categories"][0]["items"].append(dict(data["categories"][0]["items"][0]))
    with pytest.raises(ConfigError, match="duplicate item id 'youtube'"):
        load_config(write_config(tmp_path, data))


def test_handover_window_requires_window_class(tmp_path):
    data = minimal_config()
    data["categories"][0]["items"][0]["handover"] = {"type": "window"}
    with pytest.raises(ConfigError, match="window_class"):
        load_config(write_config(tmp_path, data))


def test_command_must_be_array(tmp_path):
    data = minimal_config()
    data["categories"][0]["items"][0]["launch"] = {"command": "firefox https://youtube.com/"}
    with pytest.raises(ConfigError) as excinfo:
        load_config(write_config(tmp_path, data))
    message = str(excinfo.value)
    assert "command" in message
    assert "separate array values" in message


def test_relative_paths_are_resolved(tmp_path):
    data = minimal_config()
    item = data["categories"][0]["items"][0]
    item["icon"] = "icons/youtube.png"
    item["launch"]["cwd"] = "run"
    config = load_config(write_config(tmp_path, data))
    resolved_item = config["categories"][0]["items"][0]
    assert resolved_item["icon"] == str((tmp_path / "icons" / "youtube.png").resolve())
    assert resolved_item["launch"]["cwd"] == str((tmp_path / "run").resolve())


def test_defaults_are_applied(tmp_path):
    config = load_config(write_config(tmp_path, minimal_config()))
    item = config["categories"][0]["items"][0]
    assert item["handover"] is None
    assert item["subtitle"] is None
    assert item["launch"]["env"] == {}
    assert config["settings"]["fps"] == 60


def test_icon_is_discovered_from_icons_folder(tmp_path):
    icons = tmp_path / "icons"
    icons.mkdir()
    (icons / "youtube.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    config = load_config(write_config(tmp_path, minimal_config()))
    assert config["categories"][0]["items"][0]["icon"] == str((icons / "youtube.svg").resolve())


def test_screensaver_defaults_when_absent(tmp_path):
    config = load_config(write_config(tmp_path, minimal_config()))
    screensaver = config["settings"]["screensaver"]
    assert screensaver["enabled"] is True
    assert screensaver["idle_seconds"] == 300
    assert screensaver["photo_seconds"] == 10
    assert screensaver["transition_ms"] == 1200
    assert screensaver["ken_burns"] is True
    assert screensaver["folders"] == []


def test_screensaver_validation(tmp_path):
    data = minimal_config(
        settings={
            "screensaver": {
                "photo_seconds": 1,
                "idle_seconds": -5,
                "order": "reversed",
                "folders": "~/Pictures",
            }
        }
    )
    with pytest.raises(ConfigError) as excinfo:
        load_config(write_config(tmp_path, data))
    message = str(excinfo.value)
    assert "photo_seconds" in message
    assert "idle_seconds" in message
    assert "order" in message
    assert "folders" in message


def test_screensaver_show_filename(tmp_path):
    config = load_config(write_config(tmp_path, minimal_config()))
    assert config["settings"]["screensaver"]["show_filename"] is False

    data = minimal_config(settings={"screensaver": {"show_filename": True}})
    config = load_config(write_config(tmp_path, data))
    assert config["settings"]["screensaver"]["show_filename"] is True

    bad = minimal_config(settings={"screensaver": {"show_filename": "yes"}})
    with pytest.raises(ConfigError, match="show_filename"):
        load_config(write_config(tmp_path, bad))


def test_screensaver_folders_are_resolved(tmp_path):
    data = minimal_config(settings={"screensaver": {"folders": ["photos"]}})
    config = load_config(write_config(tmp_path, data))
    assert config["settings"]["screensaver"]["folders"] == [
        str((tmp_path / "photos").resolve())
    ]


def test_theme_must_be_a_colour(tmp_path):
    data = minimal_config()
    data["categories"][0]["theme"] = "blue"
    with pytest.raises(ConfigError, match="must be a colour"):
        load_config(write_config(tmp_path, data))

    data["categories"][0]["theme"] = "#f2a54a"
    config = load_config(write_config(tmp_path, data))
    assert config["categories"][0]["theme"] == "#f2a54a"


def test_empty_categories_rejected(tmp_path):
    with pytest.raises(ConfigError, match="at least one category"):
        load_config(write_config(tmp_path, {"version": 1, "categories": []}))


def test_bad_fps_rejected(tmp_path):
    with pytest.raises(ConfigError, match="fps"):
        load_config(write_config(tmp_path, minimal_config(settings={"fps": 45})))


def test_all_errors_are_reported_together(tmp_path):
    data = minimal_config(settings={"fps": 45})
    item = data["categories"][0]["items"][0]
    item["launch"]["command"] = "nope"
    item["handover"] = {"type": "bogus"}
    with pytest.raises(ConfigError) as excinfo:
        load_config(write_config(tmp_path, data))
    message = str(excinfo.value)
    assert "fps" in message
    assert "command" in message
    assert "handover.type" in message


def test_console_subcategories_route_roms(tmp_path):
    from mediahub.library import apply_library

    raw = json.loads(EXAMPLE.read_text())
    games = raw["categories"][1]
    games["subcategories"] = [
        {"id": "snes", "title": "Super Nintendo"},
        {"id": "nes", "title": "Nintendo 8-bit"},
    ]
    snes = raw["emulators"][0]
    snes.update(category="snes", rom_dirs=[str(tmp_path)])
    raw["emulators"].append(dict(snes, id="nes-test", category="nes", extensions=[".nes"]))
    (tmp_path / "Harvest Moon.sfc").touch()
    (tmp_path / "NES Game.nes").touch()

    config = validate(raw, tmp_path)
    assert apply_library(config) == []
    games = config["categories"][1]
    assert [item["id"] for item in games["items"]] == ["steam-big-picture"]
    super_nintendo, nintendo = games["subcategories"]
    assert super_nintendo["items"] == [find_item(config, "rom-harvest-moon")]
    assert nintendo["items"] == [find_item(config, "rom-nes-game")]


def test_subcategory_id_cannot_duplicate_top_level_id(tmp_path):
    raw = minimal_config()
    raw["categories"][0]["subcategories"] = [{"id": "streaming", "title": "Duplicate"}]
    with pytest.raises(ConfigError, match=r"categories\[0\]\.subcategories\[0\]\.id: duplicate"):
        validate(raw, tmp_path)

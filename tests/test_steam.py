import pytest

from mediahub.steam import scan_steam_games


def manifest(root, app_id, title, *, flags=4, directory=None, installed=True):
    steamapps = root / "steamapps"
    steamapps.mkdir(parents=True, exist_ok=True)
    directory = title if directory is None else directory
    if installed:
        (steamapps / "common" / directory).mkdir(parents=True, exist_ok=True)
    path = steamapps / f"appmanifest_{app_id}.acf"
    path.write_text(
        f'"AppState" {{ "appid" "{app_id}" "name" "{title}" '
        f'"StateFlags" "{flags}" "installdir" "{directory}" }}', encoding="utf-8"
    )
    return path


@pytest.mark.parametrize("root_path", [
    ".local/share/Steam", ".steam/debian-installation",
    "snap/steam/common/.local/share/Steam",
])
def test_scans_default_client_paths(tmp_path, root_path):
    manifest(tmp_path / root_path, "413150", "Stardew Valley", flags=6)
    games = scan_steam_games(home=tmp_path)
    assert [(game.app_id, game.title, game.logo) for game in games] == [
        ("413150", "Stardew Valley", None)
    ]


def test_scans_modern_and_legacy_library_paths_and_deduplicates(tmp_path):
    root = tmp_path / "xdg" / "Steam"
    modern = tmp_path / 'Games "SSD"'
    legacy = tmp_path / "Second Disk"
    manifest(root, "100", "Duplicate")
    manifest(modern, "100", "Duplicate on SSD")
    manifest(modern, "200", "Äventyr")
    manifest(legacy, "300", "Another Game")
    alias = tmp_path / ".steam" / "steam"
    alias.parent.mkdir()
    alias.symlink_to(root, target_is_directory=True)
    escaped = str(modern).replace('"', '\\"')
    (root / "steamapps/libraryfolders.vdf").write_text(
        f'"LibraryFolders" {{ // steam libraries\n "0" {{ "path" "{root}" }} '
        f'"1" {{ "PATH" "{escaped}" "apps" {{ "200" "1" "999" "1" }} }} '
        f'"2" "{legacy}" "3" "unused-relative-path" }}', encoding="utf-8"
    )

    games = scan_steam_games(home=tmp_path, data_home=root.parent)
    assert [(game.app_id, game.title) for game in games] == [
        ("300", "Another Game"), ("100", "Duplicate"), ("200", "Äventyr"),
    ]


def test_ignores_runtimes_but_not_games_with_similar_names(tmp_path):
    root = tmp_path / ".local/share/Steam"
    manifest(root, "228980", "Steamworks Common Redistributables")
    manifest(root, "11", "Proton 9.0 (Beta)")
    manifest(root, "12", "Proton Experimental")
    manifest(root, "13", "Steam Linux Runtime 4.0")
    manifest(root, "14", "Custom Compatibility")
    (root / "steamapps/common/Custom Compatibility/compatibilitytool.vdf").touch()
    manifest(root, "15", "Proton Pulse")
    assert [game.app_id for game in scan_steam_games(home=tmp_path)] == ["15"]


def test_resolves_flat_and_hashed_logos_from_the_client_cache(tmp_path):
    root = tmp_path / ".local/share/Steam"
    external = tmp_path / "external"
    manifest(root, "50", "Flat")
    manifest(external, "60", "Hashed")
    manifest(external, "70", "Legacy")
    (root / "steamapps/libraryfolders.vdf").write_text(
        f'"libraryfolders" {{ "1" "{external}" }}', encoding="utf-8"
    )
    cache = root / "appcache/librarycache"
    hashed = cache / "60" / ("a" * 40) / "logo.png"
    flat = cache / "50/logo.png"
    legacy = cache / "70_logo.png"
    for logo in [flat, hashed, legacy]:
        logo.parent.mkdir(parents=True, exist_ok=True)
        logo.touch()
    assert [game.logo for game in scan_steam_games(home=tmp_path)] == [flat, hashed, legacy]


def test_skips_incomplete_and_malformed_manifests(tmp_path):
    root = tmp_path / ".local/share/Steam"
    manifest(root, "11", "Still Installing", flags=2)
    manifest(root, "12", "Missing Files", installed=False)
    manifest(root, "13", "Mismatch").rename(root / "steamapps/appmanifest_14.acf")
    manifest(root, "15", "Unclosed").write_text('"AppState" { "appid" "15"')
    manifest(root, "16", "Outside", directory="../outside")
    manifest(root, "17", "Valid")
    (root / "steamapps/libraryfolders.vdf").write_bytes(b"\xff")

    assert [game.app_id for game in scan_steam_games(home=tmp_path)] == ["17"]


def test_import_keeps_curated_tile_and_adds_only_installed_games(tmp_path):
    from mediahub.config import validate, find_item
    from mediahub.steam import apply_steam_library

    root = tmp_path / '.local/share/Steam'
    manifest(root, '413150', 'Stardew Valley')
    manifest(root, '427520', 'Factorio')
    config = validate({'version': 1, 'categories': [{'id': 'games', 'title': 'Spel', 'subcategories': [
        {'id': 'steam', 'title': 'Steam', 'items': [{'id': 'stardew-valley', 'title': 'My Stardew',
          'launch': {'command': ['steam', '-applaunch', '413150']}}]},
    ]}]}, tmp_path)
    for _ in range(2):
        apply_steam_library(config, scan_steam_games(home=tmp_path), '/bin/steam')
    section = config['categories'][0]['subcategories'][0]
    assert [item['id'] for item in section['items']] == ['stardew-valley', 'steam-427520']
    assert find_item(config, 'stardew-valley')['title'] == 'My Stardew'
    game = find_item(config, 'steam-427520')
    assert game['launch']['command'] == ['/bin/steam', '-applaunch', '427520']
    assert game['steam_app_id'] == '427520' and game['handover']['detached_launch']
    apply_steam_library(config, [], '/bin/steam')
    assert [item['id'] for item in section['items']] == ['stardew-valley']

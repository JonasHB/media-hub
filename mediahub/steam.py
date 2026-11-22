"""Read-only discovery of locally installed Steam games on Linux."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SteamGame:
    app_id: str
    title: str
    logo: Path | None = None


_TOKEN = re.compile(r'\s+|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')
_MANIFEST = re.compile(r'appmanifest_([1-9][0-9]*)\.acf')
_TOOL_NAME = re.compile(
    r"(?:Proton (?:[0-9]+(?:\.[0-9]+)*(?:-[0-9]+)?|Experimental|Hotfix)"
    r"|Steam Linux Runtime(?: [0-9]+(?:\.[0-9]+)*)?)(?: \([^()]+\))?",
    re.IGNORECASE,
)


def _read_vdf(path: Path) -> dict:
    """Read the text KeyValues subset used by Steam's library and app state files."""
    try:
        text = path.read_text(encoding="utf-8-sig")
        stack: list[tuple[dict, str]] = []
        current: dict = {}
        key = None
        offset = 0
        while offset < len(text):
            match = _TOKEN.match(text, offset)
            if match is None:
                return {}
            token = match[0]
            offset = match.end()
            if token.isspace() or token.startswith("//"):
                continue
            if token == "{":
                if key is None or len(stack) >= 64:
                    return {}
                stack.append((current, key))
                current, key = {}, None
            elif token == "}":
                if key is not None or not stack:
                    return {}
                child = current
                current, parent_key = stack.pop()
                current[parent_key] = child
            else:
                if token.startswith('"'):
                    token = re.sub(r'\\(["\\])', r'\1', token[1:-1])
                if key is None:
                    key = token.casefold()
                else:
                    current[key], key = token, None
        return current if not stack and key is None else {}
    except (OSError, UnicodeError):
        return {}


def _client_roots(home: Path, data_home: Path) -> tuple[Path, ...]:
    return (
        home / "snap/steam/common/.local/share/Steam",
        data_home / "Steam",
        home / ".local/share/Steam",
        home / ".steam/steam",
        home / ".steam/root",
        home / ".steam/debian-installation",
    )


def _library_roots(root: Path) -> Iterator[Path]:
    yield root
    folders = _read_vdf(root / "steamapps/libraryfolders.vdf").get("libraryfolders")
    if not isinstance(folders, dict):
        return
    for key, value in folders.items():
        if not re.fullmatch(r"[0-9]+", key):
            continue
        path = value.get("path") if isinstance(value, dict) else value
        if isinstance(path, str) and "\x00" not in path and Path(path).is_absolute():
            yield Path(path)


def _resolve(path: Path) -> Path | None:
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None


def _find_logo(cache: Path, app_id: str) -> Path | None:
    app_cache = cache / app_id
    if (logo := app_cache / "logo.png").is_file():
        return logo
    for logo in sorted(app_cache.glob("*/logo.png")):
        if re.fullmatch(r"[0-9a-f]{40}", logo.parent.name) and logo.is_file():
            return logo
    if (logo := cache / f"{app_id}_logo.png").is_file():
        return logo
    return None


def _installed_game(path: Path) -> SteamGame | None:
    match = _MANIFEST.fullmatch(path.name)
    if match is None:
        return None
    app_id = match[1]
    state = _read_vdf(path).get("appstate")
    if not isinstance(state, dict) or state.get("appid") != app_id:
        return None
    title = state.get("name")
    directory = state.get("installdir")
    flags = state.get("stateflags")
    if not isinstance(title, str) or not isinstance(directory, str) or not isinstance(flags, str):
        return None
    if not title.strip() or not re.fullmatch(r"[0-9]{1,10}", flags) or not int(flags) & 4:
        return None
    if not directory or directory in {".", ".."} or "/" in directory or "\x00" in directory:
        return None
    install_path = path.parent / "common" / directory
    if not install_path.is_dir():
        return None
    if app_id == "228980" or _TOOL_NAME.fullmatch(title.strip()):
        return None
    if (install_path / "compatibilitytool.vdf").is_file():
        return None
    return SteamGame(app_id, title.strip())


def scan_steam_games(*, home: Path | None = None, data_home: Path | None = None) -> list[SteamGame]:
    """Return one entry per installed app ID, ordered by title, with local logos."""
    if home is None:
        home = Path.home()
        if data_home is None:
            xdg_data_home = Path(os.environ.get("XDG_DATA_HOME", ""))
            if xdg_data_home.is_absolute():
                data_home = xdg_data_home
    games: dict[str, SteamGame] = {}
    caches: list[Path] = []
    seen_clients: set[Path] = set()
    seen_libraries: set[Path] = set()
    for candidate in _client_roots(home, data_home or home / ".local/share"):
        root = _resolve(candidate)
        if root is None or root in seen_clients:
            continue
        seen_clients.add(root)
        caches.append(root / "appcache/librarycache")
        for library in _library_roots(root):
            steamapps = _resolve(library / "steamapps")
            if steamapps is None or steamapps in seen_libraries:
                continue
            seen_libraries.add(steamapps)
            try:
                for manifest in sorted(steamapps.glob("appmanifest_*.acf")):
                    game = _installed_game(manifest)
                    if game is not None:
                        games.setdefault(game.app_id, game)
            except OSError:
                continue
    result = []
    for game in sorted(games.values(), key=lambda game: (game.title.casefold(), game.app_id)):
        logo = None
        for cache in caches:
            try:
                logo = _find_logo(cache, game.app_id)
            except OSError:
                continue
            if logo is not None:
                break
        result.append(SteamGame(game.app_id, game.title, logo))
    return result


def apply_steam_library(config: dict, games: list[SteamGame], executable: str) -> None:
    """Populate Spel → Steam without rewriting configuration or duplicating manual tiles."""
    from .library import iter_categories

    parent = next((category for category in config['categories'] if category['id'] == 'games'), None)
    if parent is None:
        return
    section = next((child for child in parent['subcategories'] if child['id'] == 'steam'), None)
    if section is None:
        if not games or any(category['id'] == 'steam' for category in iter_categories(config['categories'])):
            return
        section = {'id': 'steam', 'title': 'Steam', 'items': [], 'subcategories': [], 'theme': None}
        parent['subcategories'].append(section)
        for item in list(parent['items']):
            if item['id'] == 'steam-big-picture':
                parent['items'].remove(item)
                section['items'].append(item)
    section['items'][:] = [item for item in section['items'] if not item.get('steam_discovered')]
    known = set()
    for item in section['items']:
        args = item['launch']['command']
        if len(args) >= 3 and Path(args[0]).name == 'steam' and args[1] == '-applaunch' and args[2].isdigit():
            item['steam_app_id'] = args[2]
            known.add(args[2])
    item_ids = {item['id'] for category in iter_categories(config['categories']) for item in category['items']}
    for game in games:
        item_id = f'steam-{game.app_id}'
        if game.app_id in known or item_id in item_ids:
            continue
        section['items'].append({
            'id': item_id, 'title': game.title, 'subtitle': None,
            'icon': str(game.logo) if game.logo else None, 'steam_app_id': game.app_id,
            'steam_discovered': True,
            'launch': {'command': [executable, '-applaunch', game.app_id], 'cwd': None, 'env': {}},
            'handover': {'type': 'window', 'window_class': game.title, 'start_timeout_ms': 90000,
                         'restore_focus': True, 'close_strategy': 'graceful', 'fullscreen': False,
                         'detached_launch': True},
        })

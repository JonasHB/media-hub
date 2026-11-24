---
name: media-hub-config
description: "Use when configuring Media Hub. Validate and apply edits."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [media-hub, configuration, htpc]
    related_skills: [codebase-inspection]
---

# Media Hub configuration

## When to Use

Use for locating, editing, validating, or rolling back Media Hub settings, tiles, emulators, and photo screensaver behavior (including controller input), or adding ROMs to a configured library.

Reply briefly in Swedish by default. State what changed, what was verified, and any remaining blocker; omit process recap.

Source checkout: `/home/jonas/repo/media-hub`. Read `AGENTS.md`, `config/example.json`, and `mediahub/config.py` there for schema and project conventions. The app is a Python/PySide6 QML launcher with SDL2 gamepad input, X11 window handover, a ROM library, and a photo screensaver.

## Locate the configuration in use

- Installed copy normally lives at `~/.local/share/media-hub`; `MEDIAHUB_PREFIX` can change it. Inspect `Exec` and `Path` in `${XDG_DATA_HOME:-$HOME/.local/share}/applications/media-hub.desktop` and `${XDG_CONFIG_HOME:-$HOME/.config}/autostart/media-hub.desktop`, and check the running process argv and working directory. The generated user autostart unit can be inactive while the app is running; check the process rather than trusting the unit alone.
- Default config is `${XDG_CONFIG_HOME:-$HOME/.config}/media-hub/config.json`; `--config PATH` overrides it. A running process may have a different XDG environment; inspect only relevant variables, not the full environment. `config/example.json` is a template, not the live file. The app reads config at startup, not on file changes.
- Logs default to `${XDG_STATE_HOME:-$HOME/.local/state}/media-hub/media-hub.log`; `--log-file` and `--no-log-file` can override logging.

## Edit, validate, apply

1. Inspect only the relevant JSON fields; avoid exposing secrets in `launch.env` or backups. Resolve symlinks deliberately rather than replacing one accidentally. Make a private timestamped backup and stage a candidate in the same directory as the real config so relative paths and auto-icons resolve identically.
2. Change only requested fields, preserving unrelated values and existing permissions. Select categories/items/emulators by ID rather than hardcoding array positions.
3. From the installed working directory, run the installed validator without starting the UI or executing tile commands:
   ```sh
   .venv/bin/python -c 'import sys; from mediahub.config import load_config; load_config(sys.argv[1]); print("Config valid")' "$candidate"
   ```
   Schema validation does not prove programs, media directories, Flatpak permissions, or X11 handover work. Check relevant dependencies separately without launching them unless requested.
4. If valid, replace the config atomically (same filesystem), validate the final file at its exact path, and read back the specific changed fields. Restore from the backup if verification fails. Apply the same staging and validation when rolling back.
5. Restart only if authorized and safe to interrupt the graphical session: close the launcher normally and reopen it via its desktop entry in that session. Do not use sudo or kill active games/streaming apps. Verify the new process and startup logs; if not restarted, explicitly say the edit takes effect on next launch. No reinstall for JSON-only changes. The installer preserves existing config and icons; do not touch Flex Launcher or AntiMicroX in routine config work.

## Verify repo changes on the installed launcher

- Follow the repo’s `AGENTS.md` for delivery. After running the installer, compare affected code/assets against the installed copies with `cmp`. Verify the live JSON separately with the installed validator: the installer preserves it, so new settings in the example do not activate themselves. When migrating a ROM category, run `apply_library` and check the expected title under the intended category in the resulting model.
- Test visual navigation in an isolated Qt subprocess with `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software`. Reuse the QML setup in `tests/test_navigation.py` and send explicit `QTest` keys to the test window. Assert the target category before taking a screenshot; relying on CLI key playback or attaching a real controller to the test can trigger a tile launch. Use synthetic ROMs and a temporary config or an in-memory fixture, not the live library.
- For selection skipping in long game rows, reproduce with a synthetic library large enough to scroll and a pointer over the tiles during animation. Mouse hover must not overwrite directional selection during animated scrolling or with the pointer hidden in fullscreen; keep click activation available.
- For tile logos, folder badges, artwork lookup, or blurry icons, follow `references/tile-artwork.md` before changing assets or QML.

## Photo screensaver and controller changes

- Scan the configured photo folders when the slideshow starts, not when the launcher starts. Keep the active deck stable until the next slideshow; the automatic idle timer must still retry when the folders are empty. Test by creating a photo after QML has loaded and navigating to it without restarting the launcher.

1. Keep the interaction scoped to the active slideshow: D-pad and both sticks left/right and LB/RB browse, up/down adjusts by 0.5 s, and A toggles automatic playback without closing the slideshow. Display the actual interval with one decimal and `s` for two seconds after the last adjustment, then fade it out. Keep manual browsing available during pause and preserve the remaining countdown when resuming an unchanged photo.
2. Exercise the SDL → QML path in `tests/test_navigation.py` with a virtual SDL controller and synthetic local photos. Assert image order, pause/resume, the duration text and its disappearance; use `QTest.qWait()` in a bounded polling loop for asynchronous changes. Set `SLIDESHOW_TEST_SCREENSHOT` to an absolute PNG path to capture the paused overlay offscreen without disturbing the live desktop. Keep slideshow-only inputs from changing launcher behavior outside the slideshow.
3. Use the repo test interpreter, or the installed `~/.local/share/media-hub/.venv/bin/python` from the checkout if it already has the test dependencies. On this host, run `DISPLAY=:0 SDL_GAMECONTROLLER_IGNORE_DEVICES=0x045e/0x028e <python> -m pytest -q` when the X11 session is available: `DISPLAY` enables handover tests, and the SDL filter prevents the physical Xbox 360 controller from taking the virtual test controller's slot. The navigation subprocess still runs offscreen.
4. If real input wakes the slideshow while the virtual test passes, check the AntiMicroX profile via `references/controller-profiles.md`: duplicate emulated keyboard or mouse input can close the slideshow before the native SDL action takes effect. Check rather than changing unrelated profiles; distinguish virtual test coverage from a physical controller test in the handoff.

## Hermes i Media Hub

- Prioritera mikrofon och deltranskript medan användaren talar. Skilj strömmande taligenkänning från filtranskribering efter avslutad inspelning och från strömmande svarstext; verifiera varje del separat innan du kallar hela flödet strömmande. Läs `hermes-agent` och aktuella officiella API-dokument innan du väljer integration.
- Kontrollera ljudingångarna med `pactl list short sources`, uteslut `.monitor` och verifiera riktig inspelning innan du säger att mikrofonen fungerar. Föreslå lokal taligenkänning först; skicka inte mikrofonljud till en extern tjänst utan att användaren valt det.

## Firefox från streamingkaklen

- Behåll `firefox --new-window URL` och sätt `handover.fullscreen: true` på streamingkaklen med Firefox-profil. Använd fönsteröverlämningen i stället för kioskläge så att helskärm inte låser webbläsaren. Skilj webbläsarens helskärm från videospelarens helskärm. Läs tillbaka värdet för varje berört kakel och provstarta ett kakel när en omstart är godkänd.
- Lägg biblioteksbundna streaminggenvägar direkt på det valda bibliotekets katalog, inte på tjänstens startsida. För Cineasterna använder den här installationen Huddinge bibliotek (`https://www.cineasterna.com/sv/library/68/discover`) och en rund ikon. Vid en länkändring, ersätt bara URL-argumentet och läs tillbaka det tillsammans med ikon och helskärmsinställning. En verifierad genväg är inte verifierad filmuppspelning.
- Använd LB för bakåt (`Alt+Left`) och RB för framåt (`Alt+Right`) i Firefox, inte Tab. Ändra bara den aktiva Firefox-profilen i AntiMicroX; behåll Media Hubs separata utgångskombination. Se `references/controller-profiles.md` för profiländring och verifiering.

- För sökning från soffan, välj ett tangentbord som navigeras med styrkorset utan att stjäla sökrutans fokus. Kontrollera att öppningskombinationen inte krockar med Media Hubs utgång eller AntiMicroX. Se `references/controller-profiles.md` för installation och verifiering.

## Logotyper

- För spellogotyper, följ `game-emulators`: LaunchBox Clear Logo, rätt region och exakt ROM-basnamn. Verifiera bilden via den installerade appens `apply_library`.
- För streaminglogotyper, föredra tjänstens egen SVG (SVT Play publicerar exempelvis loggan i sin SVG-sprite) eller en dokumenterad SVG från Wikimedia Commons. Spara källan i `config/icons/credits.md`. Använd en ljus variant på mörka kakel och behåll användarens egna ikoner. Testa att Qt kan läsa filen och kontrollera kontrasten i en offscreen-skärmdump. En SVG med liten standardstorlek kan se suddig ut om Qt rasteriserar den före uppskalning; sätt `Image.sourceSize` utifrån kaklets visningsbredd.

## Steam games

- For Steam commands that exit before opening a game, use `handover.detached_launch: true` with a bounded `start_timeout_ms`; increasing the timeout alone does not bypass the early-exit grace. Measure the actual launcher exit code and the real window appearance; Steam Snap can return 1 even while successfully forwarding the request. Verify with the installed Handover against the actual tile and game, not just a synthetic process that exits 0. Match the real X11 `WM_CLASS`, including spaces, and verify `window ... is active` followed by `gamepad input suspended` in the launcher log. Start with the game closed because window handover watches for a new window.

- If an unwanted Steam tile is auto-imported rather than manually configured, inspect its local `appmanifest_<appid>.acf` and the filters in `mediahub/steam.py`. For a confirmed runtime or compatibility tool, add a failing fixture to `tests/test_steam.py` and filter the verified AppID rather than broadening a name match that could hide real games. Do not uninstall the dependency or edit Steam's manifests. After installation, run `mediahub.steam.scan_steam_games()` from the installed directory against the real library; verify that the tool is absent and a known game remains. Distinguish scanner verification from the running menu, which needs a launcher restart to load code changes.

## Controller acceptance for every game addition

- Whenever adding any game to Media Hub, verify controller handover from the game tile. The Xbox controller must remain active as a native gamepad in the game or emulator (including the intended player slot and mappings), but AntiMicroX desktop mouse/keyboard mappings and Media Hub navigation must be inactive while playing. Keep Xbox Guide as the sole Media Hub shortcut during play; it must return to Media Hub and restore launcher navigation. Use `references/controller-profiles.md` to inspect window-specific AntiMicroX profiles; prefer an empty profile for the game or emulator when needed rather than disabling the controller or changing unrelated profiles.
- Test from Media Hub: launch the added game, verify in-game input and absence of desktop actions, press Guide, and verify focus and navigation in Media Hub again. Configuration checks and synthetic tests are not a physical play test. If physical input cannot be verified, say exactly what remains untested rather than claiming it works.

## Add installed Steam games

- Steam tiles are auto-imported at launch and when opening Spel → Steam. Verify the installed scanner against local manifests, preserving manually curated tiles by AppID. Use Xbox X (keyboard P) for per-game AntiMicroX profile selection. Choices are stored by AppID in `steam-controller-profiles.json` beside the launcher config. Named switching requires a dedicated, empty, unshared AntiMicroX AutoProfile for that game's actual X11 window class; without it, the menu explicitly preserves the existing mapping. Do not claim automatic mouse suppression for unconfigured games. Verify named staging, rollback, and controller menu separately from physical Guide and game input.

1. Resolve the installed Steam executable with `command -v steam` and find the game’s `appmanifest_<appid>.acf` in the Steam library. Read `steamapps/libraryfolders.vdf` for additional roots; for Snap Steam start at `~/snap/steam/common/.local/share/Steam/steamapps`. Use the verified executable and `-applaunch <appid>` in the tile’s argv; do not reinstall an existing game or launch its internal binary directly.
2. Preserve Spel → Steam: Steam is a subcategory under Spel, and each game is a direct tile alongside Steam Big Picture. Convert an existing Steam tile into that subcategory without promoting Steam to a top-level category. A tile cannot have children, and the schema only allows one subcategory level. Verify the final hierarchy and launch argv with the installed `load_config` and `find_item`. For Steam artwork, see `references/tile-artwork.md`.
3. Read the actual game window’s class with `DISPLAY=:0 wmctrl -lx` and `xprop -id <window-id> WM_CLASS` in the same X11 session. Pass a complete instance or class string (including spaces) to the installed `mediahub.handover.class_matches` before saving the rule: older builds split on whitespace and can reject a valid literal class. If necessary, regression-test the observed tuple, deploy the matcher fix, and verify the installed copy. Handover waits for a new window, so exit any existing game instance normally before testing tile launch. Apply the controller acceptance checks above separately; do not count the existing instance or a saved AntiMicroX rule as a successful live test.

## Find or add ROMs

1. Read the relevant emulator's `rom_dirs` and `extensions` from the active config before recommending a destination or format; examples and defaults do not prove what the library scans. Use a configured directory when possible so no JSON edit is needed.
2. When searching for a ROM, distinguish a listing from a verified download. Respect the user's chosen source and stop trying it once they rule it out. Do not report an untested alternative as a working download.
3. For archive imports, inventory every archive and inspect its members before writing. Read only supported ROM members with `zipfile.ZipFile.read()` rather than extracting whole archives: this checks the member CRC and skips bundled HTML/readme files and archive paths. Check the ROM header (for iNES, `NES\x1a`), match a Clear Logo to the actual game/platform/region, and save it with the exact ROM stem. Use exclusive writes unless overwriting is authorized. Keep original archives unless asked to remove them.
4. Verify the actual edition, not just the archive name: a sports title may be bundled in a two-game cartridge. If the user wants the standalone game, do not rename the bundle to pass it off as standalone. For library removal or replacement, move the old ROM and matching art outside all recursively scanned ROM roots so it disappears without losing the files.
5. Run the installed `load_config` and `apply_library` against the active config. Check each expected ROM path in the generated launch command and the exact resolved logo path; confirm removed entries are absent. Report separately whether the files and tiles were verified or the games were actually played. The live launcher picks up library changes on next launch.

## Schema traps

- Version 1, strict JSON; unknown keys rejected. At least one top-level category. A top-level category needs direct items or nonempty `subcategories`; subcategories may start empty. Category IDs are unique across both levels, and tile IDs are globally unique. To move SNES ROMs under Spel → Super Nintendo, copy `subcategories` from the repo example into `games` and set Snes9x `category` to `snes`. Nintendo 8-bit (`nes`) needs a separately configured NES emulator. An older installed copy rejects `subcategories`: deploy compatible code before changing live JSON. `settings.screensaver` is nested, not top-level. `idle_seconds: 0` disables automatic activation only; `enabled: false` disables the screensaver. Supported FPS values: 30 and 60.
- App tiles use `launch.command` as an argv array. Omit `launch.cwd` if unset: despite the README example, explicit `null` is rejected. `launch.env` values must be strings. `handover.type: "window"` requires `window_class`; use `xprop WM_CLASS` on the target window in the X11 session when troubleshooting.
- Paths such as `icon`, `launch.cwd`, ROM and photo directories expand `~` and resolve relative to the config directory. An omitted tile icon is looked up as `icons/<item-id>.(png|jpg|jpeg|webp|svg)` beside the config. Emulator entries reference an existing category, require `rom_dirs`, dot-prefixed `extensions`, `{rom}` in the command, and window handover. See `mediahub/library.py` for cover discovery.
- If changing the schema or shipped defaults, follow repo `AGENTS.md`: update validation, tests, README, and the example together. Check QML fallback values too. If the user wants the new default on this installation, inspect the live override and update it separately using the staged config workflow above; an explicit value wins over the shipped default. Never commit live user config or secrets.

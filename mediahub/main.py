from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QEvent, QLocale, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine

from . import __version__
from .config import ConfigError, load_config
from .gamepad import Gamepad
from .handover import Handover
from .library import apply_library, report_missing_icons

APP_ROOT = Path(__file__).resolve().parent.parent
QML_DIR = APP_ROOT / "qml"


def default_config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "media-hub" / "config.json"


def default_log_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / "media-hub" / "media-hub.log"


def setup_logging(log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(
                RotatingFileHandler(log_file, maxBytes=512 * 1024, backupCount=2)
            )
        except OSError:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="media-hub", description="Local HTPC launcher")
    parser.add_argument("--config", type=Path, default=None, help="path to config JSON")
    parser.add_argument("--windowed", action="store_true", help="run in a window instead of fullscreen")
    parser.add_argument(
        "--size",
        default="1280x720",
        metavar="WxH",
        help="window size in windowed mode, e.g. 1920x1080 (default: 1280x720)",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        default=None,
        help="save a screenshot to this path after startup and exit (for testing)",
    )
    parser.add_argument(
        "--keys",
        default="",
        metavar="KEYS",
        help="comma-separated key names to send after startup, e.g. Down,Right,Return (testing)",
    )
    parser.add_argument(
        "--screenshot-delay",
        type=int,
        default=1300,
        metavar="MS",
        help="delay before the screenshot is taken (default: 1300)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="also write logs to this file (for SSH troubleshooting)",
    )
    parser.add_argument("--no-log-file", action="store_true", help="disable the default log file")
    parser.add_argument("--version", action="version", version=f"media-hub {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config_path = args.config or default_config_path()

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"media-hub: configuration not found: {config_path}", file=sys.stderr)
        print(
            f"  copy {APP_ROOT / 'config' / 'example.json'} to {default_config_path()} and edit it",
            file=sys.stderr,
        )
        return 2
    except ConfigError as exc:
        print(f"media-hub: configuration error in {config_path}:", file=sys.stderr)
        for line in str(exc).splitlines():
            print(f"  - {line}", file=sys.stderr)
        return 2

    library_warnings = apply_library(config)

    if args.no_log_file:
        log_file = None
    elif args.log_file is not None:
        log_file = args.log_file
    else:
        log_file = default_log_path()
    setup_logging(log_file)

    QLocale.setDefault(QLocale(QLocale.Language.Swedish, QLocale.Country.Sweden))

    try:
        window_width, window_height = (int(value) for value in args.size.lower().split("x"))
    except ValueError:
        print(f"media-hub: invalid --size {args.size!r}, expected WxH", file=sys.stderr)
        return 2

    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("media-hub")
    app.setApplicationDisplayName("Media Hub")
    app.setDesktopFileName("media-hub")
    QLocale.setDefault(QLocale(QLocale.Language.Swedish, QLocale.Country.Sweden))

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("configJson", json.dumps(config, ensure_ascii=False))
    context.setContextProperty("startWindowed", args.windowed)
    context.setContextProperty("windowWidth", window_width)
    context.setContextProperty("windowHeight", window_height)
    context.setContextProperty(
        "screenshotPath", str(args.screenshot) if args.screenshot is not None else ""
    )
    context.setContextProperty("screenshotDelay", args.screenshot_delay)
    handover = Handover(config, engine)
    context.setContextProperty("launcher", handover)
    gamepad = Gamepad(engine, config["settings"]["exit_combo"])
    context.setContextProperty("gamepad", gamepad)
    app.aboutToQuit.connect(gamepad.shutdown)

    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        print("media-hub: failed to load the QML interface", file=sys.stderr)
        return 1

    window = engine.rootObjects()[0]
    handover.set_launcher_window(window)
    handover.externalActive.connect(lambda _item_id: gamepad.setActive(False))
    handover.externalClosed.connect(lambda _item_id: gamepad.setActive(True))
    gamepad.guidePressed.connect(handover.request_close)
    gamepad.exitComboPressed.connect(handover.request_close)

    library_log = logging.getLogger("mediahub.library")
    for warning in library_warnings:
        library_log.warning("%s", warning)
    for category_id, item_id, title in report_missing_icons(config):
        library_log.info(
            "ingen ikon för %s (%s/%s) - lägg till icons/%s.png i konfigurationsmappen",
            title,
            category_id,
            item_id,
            item_id,
        )

    keys = [name.strip() for name in args.keys.split(",") if name.strip()]
    for offset, name in enumerate(keys):
        key = getattr(Qt.Key, f"Key_{name}", None)
        if key is None:
            print(f"media-hub: unknown key name: {name}", file=sys.stderr)
            return 2

        def send(key_code: int = key) -> None:
            event = QKeyEvent(QEvent.Type.KeyPress, key_code, Qt.KeyboardModifier.NoModifier)
            QGuiApplication.postEvent(window, event)

        QTimer.singleShot(600 + offset * 350, send)

    return app.exec()

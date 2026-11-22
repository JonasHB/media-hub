from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from Xlib import X, Xatom, error as xerror, protocol

from .config import find_item
from .steam import apply_steam_library, scan_steam_games

log = logging.getLogger(__name__)

POLL_INTERVAL_MS = 75
PROCESS_EXIT_GRACE = 3.0
CLOSE_TIMEOUT = 8.0
KILL_GRACE = 3.0


def class_matches(configured: str, wm_class: tuple[str, str] | None) -> bool:
    if wm_class is None:
        return False
    parts = configured.split()
    instance, klass = wm_class
    instance = (instance or "").lower()
    klass = (klass or "").lower()

    if configured.strip().lower() in (instance, klass):
        return True
    if len(parts) != 2:
        return False
    first, second = parts[0].lower(), parts[1].lower()
    return (first, second) == (instance, klass) or (second, first) == (instance, klass)


class Handover(QObject):
    started = Signal(str)
    errorOccurred = Signal(str)
    externalActive = Signal(str)
    externalClosed = Signal(str)
    busyChanged = Signal()

    def __init__(self, config: dict, parent: QObject | None = None, *,
                 steam_profiles=None, selections_path: Path | None = None,
                 steam_executable: str | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._steam_profiles = steam_profiles
        self._steam_executable = steam_executable
        self._selections_path = selections_path
        self._profile_selections = self._load_profile_selections()
        self._item: dict | None = None
        self._process: subprocess.Popen | None = None
        self._window_id: int | None = None
        self._existing_windows: set[int] = set()
        self._deadline = 0.0
        self._grace_deadline: float | None = None
        self._close_deadline: float | None = None
        self._kill_deadline: float | None = None
        self._launcher_window = None
        self._display = None
        self._started_at = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    def set_launcher_window(self, window) -> None:
        self._launcher_window = window

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._item is not None

    @Slot(result=str)
    def refreshSteamSection(self) -> str:
        if self.busy or not self._steam_executable:
            return ""
        apply_steam_library(self._config, scan_steam_games(), self._steam_executable)
        for category in self._config['categories']:
            if category['id'] == 'games':
                for section in category['subcategories']:
                    if section['id'] == 'steam':
                        return json.dumps(section, ensure_ascii=False)
        return ""

    def _load_profile_selections(self) -> dict[str, str]:
        if self._selections_path is not None:
            try:
                data = json.loads(self._selections_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {app_id: profile for app_id, profile in data.items()
                            if app_id.isdigit() and isinstance(profile, str)}
            except FileNotFoundError:
                pass
            except (OSError, ValueError) as error:
                log.warning("Could not read Steam controller selections: %s", error)
        return {}

    @Slot(str, result="QVariantList")
    def controllerProfiles(self, item_id: str) -> list[dict]:
        item = find_item(self._config, item_id)
        if not item or not item.get("steam_app_id"):
            return []
        handover = item.get("handover") or {}
        supported = bool(self._steam_profiles and self._steam_profiles.supports(handover.get("window_class") or ""))
        choices = self._steam_profiles.choices() if supported and self._steam_profiles else []
        selected = self._profile_selections.get(item["steam_app_id"], "")
        return [{"action": "", "title": "Ingen mappning" if supported else "Behåll befintlig mappning",
                 "subtitle": "Spelet använder Xbox-kontrollen direkt" if supported else
                             "Ingen dedikerad AntiMicroX-regel för spelet",
                 "selected": selected not in {value for value, _ in choices}},
                *({"action": value, "title": title, "subtitle": "AntiMicroX-profil", "selected": selected == value}
                  for value, title in choices)]

    @Slot(str, str, result=bool)
    def setControllerProfile(self, item_id: str, profile: str) -> bool:
        item = find_item(self._config, item_id)
        if self.busy or self._selections_path is None or item is None or not any(
            choice["action"] == profile for choice in self.controllerProfiles(item_id)
        ):
            return False
        app_id = item["steam_app_id"]
        selections = dict(self._profile_selections)
        if profile:
            selections[app_id] = profile
        else:
            selections.pop(app_id, None)
        temp = None
        try:
            self._selections_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                             dir=self._selections_path.parent) as stream:
                temp = Path(stream.name)
                json.dump(selections, stream, ensure_ascii=False)
            temp.replace(self._selections_path)
            self._profile_selections = selections
            return True
        except OSError as error:
            log.warning("Could not save Steam controller selection: %s", error)
            return False
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    @Slot(str)
    def start(self, item_id: str) -> None:
        if self._item is not None:
            log.info("ignoring start of %s: %s is active", item_id, self._item["id"])
            return

        item = find_item(self._config, item_id)
        if item is None:
            self.errorOccurred.emit(f"Okänd post: {item_id}")
            return

        command = item["launch"]["command"]
        if not command:
            self.errorOccurred.emit(f"{item['title']} saknar startkommando")
            return

        handover = item["handover"]
        window_class = handover["window_class"] if handover else None
        self._existing_windows = (
            self._matching_window_ids(window_class, item.get("steam_app_id")) if window_class else set()
        )

        env = dict(os.environ)
        env.update(item["launch"]["env"])

        app_id = item.get("steam_app_id")
        profile = self._profile_selections.get(app_id) if app_id else None
        if profile and self._steam_profiles and not self._steam_profiles.activate(profile, window_class or ""):
            self.errorOccurred.emit("Kunde inte aktivera den valda kontrollprofilen. Välj ingen mappning med X.")
            return

        try:
            self._process = subprocess.Popen(
                command,
                cwd=item["launch"]["cwd"],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError:
            if self._steam_profiles:
                self._steam_profiles.restore()
            self.errorOccurred.emit(f"Hittade inte programmet: {command[0]}")
            return
        except OSError as exc:
            if self._steam_profiles:
                self._steam_profiles.restore()
            self.errorOccurred.emit(f"Kunde inte starta {item['title']}: {exc}")
            return

        self._item = item
        timeout_ms = handover["start_timeout_ms"] if handover else 20000
        self._deadline = time.monotonic() + timeout_ms / 1000
        self._grace_deadline = None
        self._window_id = None
        self._started_at = time.monotonic()
        log.info("started %s (%s)", item["id"], " ".join(command))
        self.busyChanged.emit()
        self.started.emit(item_id)

    def _display_conn(self):
        if self._display is None:
            from Xlib import display

            self._display = display.Display()
        return self._display

    def _top_level_windows(self) -> list:
        display = self._display_conn()
        try:
            root = display.screen().root
            client_list = root.get_full_property(
                display.intern_atom("_NET_CLIENT_LIST"), Xatom.WINDOW
            )
            if client_list is not None and client_list.value:
                return [
                    display.create_resource_object("window", window_id)
                    for window_id in client_list.value
                ]

            windows = []
            for top in root.query_tree().children:
                if self._safe_window_class(top) is not None:
                    windows.append(top)
                    continue
                try:
                    children = top.query_tree().children
                except xerror.XError:
                    continue
                windows.extend(
                    child for child in children if self._safe_window_class(child) is not None
                )
            return windows
        except (xerror.XError, OSError) as exc:
            log.warning("could not list X windows: %s", exc)
            return []

    @staticmethod
    def _safe_window_class(window):
        try:
            return window.get_wm_class()
        except xerror.XError:
            return None

    def _matches_window(self, window, window_class: str, app_id: str | None = None) -> bool:
        wm_class = self._safe_window_class(window)
        if app_id:
            try:
                atom = self._display_conn().intern_atom("_STEAM_GAME", only_if_exists=True)
                prop = window.get_full_property(atom, Xatom.CARDINAL) if atom else None
                if prop is not None and len(prop.value) and prop.value[0]:
                    return str(prop.value[0]) == str(app_id)
            except xerror.XError:
                return False
            for name in wm_class or ():
                normalized = name.lower()
                if normalized.startswith("steam_app_") and normalized[10:].isdigit():
                    return normalized == f"steam_app_{app_id}"
            if process_app_id := self._window_process_app_id(window):
                return process_app_id == str(app_id)
        return class_matches(window_class, wm_class)

    def _window_process_app_id(self, window) -> str | None:
        try:
            display = self._display_conn()
            atom = display.intern_atom("_NET_WM_PID", only_if_exists=True)
            prop = window.get_full_property(atom, Xatom.CARDINAL) if atom else None
            if prop is None or not len(prop.value) or prop.value[0] <= 1:
                return None
            process = Path("/proc") / str(prop.value[0])
            if process.stat().st_uid != os.getuid():
                return None
            with (process / "environ").open("rb") as stream:
                for entry in stream.read(256 * 1024).split(b"\0"):
                    key, _, value = entry.partition(b"=")
                    if key in (b"SteamAppId", b"SteamGameId") and value.isdigit() and int(value) > 0:
                        return value.decode("ascii")
        except (OSError, xerror.XError, ValueError):
            pass
        return None

    def _matching_window_ids(self, window_class: str, app_id: str | None = None) -> set[int]:
        return {
            window.id for window in self._top_level_windows()
            if self._matches_window(window, window_class, app_id)
        }

    def _find_new_window(self, window_class: str, app_id: str | None = None) -> int | None:
        for window in self._top_level_windows():
            if window.id not in self._existing_windows and self._matches_window(window, window_class, app_id):
                return window.id
        return None

    def _window_exists(self, window_id: int) -> bool:
        return any(window.id == window_id for window in self._top_level_windows())

    def _poll(self) -> None:
        if self._item is None:
            return

        handover = self._item["handover"]
        if handover is None or handover["type"] != "window":
            self._reset()
            return

        now = time.monotonic()
        window_class = handover["window_class"]

        if self._window_id is None:
            found = self._find_new_window(window_class, self._item.get("steam_app_id"))
            if found is not None:
                self._window_id = found
                log.info(
                    "handover: window %#x is active after %d ms",
                    found,
                    int((now - self._started_at) * 1000),
                )
                if handover.get("fullscreen"):
                    self._request_fullscreen(found)
                self._park_launcher()
                self.externalActive.emit(self._item["id"])
                return

            status = self._process.poll() if self._process is not None else None
            if status is not None and self._grace_deadline is None and not handover.get("detached_launch"):
                self._grace_deadline = now + PROCESS_EXIT_GRACE

            if status is not None and handover.get("detached_launch") and now >= self._deadline:
                log.warning("detached start command exited with status %s", status)

            if self._grace_deadline is not None:
                if now >= min(self._grace_deadline, self._deadline):
                    self._fail_start(
                        f"{self._item['title']} avslutades utan att öppna ett fönster"
                    )
                return

            if now >= self._deadline:
                self._fail_start("inget fönster dök upp")
            return

        if not self._window_exists(self._window_id):
            log.info("handover: window %#x closed", self._window_id)
            item_id = self._item["id"]
            self._reset()
            self._restore_launcher()
            self.externalClosed.emit(item_id)
            return

        if self._close_deadline is not None and now >= self._close_deadline:
            self._close_deadline = None
            if self._process is not None and self._process.poll() is None:
                log.warning("graceful close timed out, terminating process")
                self._process.terminate()
                self._kill_deadline = now + KILL_GRACE
            else:
                log.warning("graceful close timed out and no process can be terminated")
                self.errorOccurred.emit(
                    f"Kunde inte stänga {self._item['title']} med handkontrollen"
                )

        if self._kill_deadline is not None and now >= self._kill_deadline:
            self._kill_deadline = None
            if self._process is not None and self._process.poll() is None:
                log.warning("process did not exit, killing it")
                self._process.kill()

    @Slot()
    def request_close(self) -> None:
        if self._item is None or self._window_id is None:
            return
        if self._close_deadline is not None or self._kill_deadline is not None:
            return

        handover = self._item["handover"]
        if handover is not None and handover["close_strategy"] == "kill":
            if self._process is not None and self._process.poll() is None:
                log.info("closing %s with SIGTERM", self._item["id"])
                self._process.terminate()
                self._kill_deadline = time.monotonic() + KILL_GRACE
                return
        log.info("requesting graceful close of window %#x", self._window_id)
        self._send_close(self._window_id)
        self._close_deadline = time.monotonic() + CLOSE_TIMEOUT

    def _window_object(self, window_id: int):
        return self._display_conn().create_resource_object("window", window_id)

    def _request_fullscreen(self, window_id: int) -> None:
        display = self._display_conn()
        try:
            window = self._window_object(window_id)
            fullscreen = display.intern_atom("_NET_WM_STATE_FULLSCREEN")
            event = protocol.event.ClientMessage(
                window=window,
                client_type=display.intern_atom("_NET_WM_STATE"),
                data=(32, [1, fullscreen, 0, 1, 0]),
            )
            display.screen().root.send_event(
                event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask
            )
            display.flush()
        except (xerror.XError, OSError) as exc:
            log.warning("could not request fullscreen: %s", exc)

    def _send_close(self, window_id: int) -> None:
        display = self._display_conn()
        try:
            window = self._window_object(window_id)
            protocols = display.intern_atom("WM_PROTOCOLS")
            delete = display.intern_atom("WM_DELETE_WINDOW")
            supported = window.get_full_property(protocols, Xatom.ATOM)
            if supported is None or delete not in supported.value:
                log.warning("window %#x does not announce WM_DELETE_WINDOW", window_id)
            event = protocol.event.ClientMessage(
                window=window,
                client_type=protocols,
                data=(32, [delete, X.CurrentTime, 0, 0, 0]),
            )
            window.send_event(event, event_mask=0)
            display.flush()
        except (xerror.XError, OSError) as exc:
            log.warning("could not send close request: %s", exc)

    def _fail_start(self, reason: str) -> None:
        title = self._item["title"] if self._item else "programmet"
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        log.warning("handover failed for %s: %s", title, reason)
        self._reset()
        self._restore_launcher()
        self.errorOccurred.emit(f"Kunde inte starta {title}: {reason}")

    def _reset(self) -> None:
        was_busy = self._item is not None
        if self._steam_profiles:
            self._steam_profiles.restore()
        self._item = None
        self._process = None
        self._window_id = None
        self._existing_windows = set()
        self._grace_deadline = None
        self._close_deadline = None
        self._kill_deadline = None
        if was_busy:
            self.busyChanged.emit()

    def _park_launcher(self) -> None:
        if self._launcher_window is not None:
            self._launcher_window.lower()

    def _restore_launcher(self) -> None:
        if self._launcher_window is None:
            return
        self._launcher_window.showFullScreen()
        raise_ = getattr(self._launcher_window, "raise_", None)
        if raise_ is None:
            raise_ = getattr(self._launcher_window, "raise", None)
        if raise_ is not None:
            raise_()
        self._launcher_window.requestActivate()

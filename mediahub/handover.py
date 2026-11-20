from __future__ import annotations

import logging
import os
import subprocess
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from Xlib import X, Xatom, error as xerror, protocol

from .config import find_item

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

    if len(parts) == 1:
        wanted = parts[0].lower()
        return wanted in (instance, klass)
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

    def __init__(self, config: dict, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
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
            self._matching_window_ids(window_class) if window_class else set()
        )

        env = dict(os.environ)
        env.update(item["launch"]["env"])

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
            self.errorOccurred.emit(f"Hittade inte programmet: {command[0]}")
            return
        except OSError as exc:
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

    def _matching_window_ids(self, window_class: str) -> set[int]:
        matches = set()
        for window in self._top_level_windows():
            if class_matches(window_class, self._safe_window_class(window)):
                matches.add(window.id)
        return matches

    def _find_new_window(self, window_class: str) -> int | None:
        candidates = [
            window
            for window in self._top_level_windows()
            if window.id not in self._existing_windows
        ]
        for window in candidates:
            if class_matches(window_class, self._safe_window_class(window)):
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
            found = self._find_new_window(window_class)
            if found is not None:
                self._window_id = found
                log.info(
                    "handover: window %#x is active after %d ms",
                    found,
                    int((now - self._started_at) * 1000),
                )
                if handover.get("fullscreen"):
                    self._request_fullscreen(found)
                self._hide_launcher()
                self.externalActive.emit(self._item["id"])
                return

            process_done = self._process is not None and self._process.poll() is not None
            if process_done and self._grace_deadline is None:
                self._grace_deadline = now + PROCESS_EXIT_GRACE

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
            self._show_launcher()
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
        self._show_launcher()
        self.errorOccurred.emit(f"Kunde inte starta {title}: {reason}")

    def _reset(self) -> None:
        was_busy = self._item is not None
        self._item = None
        self._process = None
        self._window_id = None
        self._existing_windows = set()
        self._grace_deadline = None
        self._close_deadline = None
        self._kill_deadline = None
        if was_busy:
            self.busyChanged.emit()

    def _hide_launcher(self) -> None:
        if self._launcher_window is not None:
            self._launcher_window.hide()

    def _show_launcher(self) -> None:
        if self._launcher_window is None:
            return
        self._launcher_window.showFullScreen()
        self._launcher_window.requestActivate()

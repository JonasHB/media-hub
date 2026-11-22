import sys
import time

import pytest
from PySide6.QtCore import QCoreApplication

from mediahub.config import validate
from mediahub.handover import Handover, class_matches

FAKE_WINDOW = """
import time
from Xlib import X, display
d = display.Display()
screen = d.screen()
w = screen.root.create_window(
    40, 40, 320, 200, 0, screen.root_depth, X.InputOutput, X.CopyFromParent,
    background_pixel=screen.white_pixel, event_mask=X.ExposureMask,
)
w.set_wm_name("Fake Player")
w.set_wm_class("Navigator", "firefox_firefox")
w.map()
d.sync()
time.sleep(30)
"""


class FakeLauncherWindow:
    def __init__(self):
        self.visible = True
        self.activations = 0
        self.raised = 0
        self.lowered = 0

    def hide(self):
        self.visible = False

    def lower(self):
        self.lowered += 1

    def raise_(self):
        self.raised += 1

    def showFullScreen(self):
        self.visible = True

    def requestActivate(self):
        self.activations += 1


def x_display_available() -> bool:
    try:
        from Xlib import display

        display.Display().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not x_display_available(), reason="no X display available")


@pytest.fixture(scope="module")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def make_config(tmp_path, command, handover=None, timeout=2000):
    raw = {
        "version": 1,
        "categories": [
            {
                "id": "apps",
                "title": "Apps",
                "items": [
                    {
                        "id": "target",
                        "title": "Target",
                        "launch": {"command": command},
                        "handover": handover
                        or {"type": "window", "window_class": "Navigator firefox_firefox", "start_timeout_ms": timeout},
                    }
                ],
            }
        ],
    }
    return validate(raw, tmp_path)


def pump(handover, seconds, until):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        handover._poll()
        if until():
            return True
        time.sleep(0.1)
    return False


def test_class_matches_literal_name_with_spaces():
    assert class_matches("stardew valley", ("Stardew Valley", "Stardew Valley"))


def test_class_matches():
    assert class_matches("Navigator firefox_firefox", ("Navigator", "firefox_firefox"))
    assert class_matches("navigator FIREFOX_firefox", ("Navigator", "firefox_firefox"))
    assert class_matches("snes9x-gtk", ("snes9x-gtk", "Snes9x-gtk"))
    assert not class_matches("Navigator firefox_firefox", ("Steam", "steam"))
    assert not class_matches("a b c", ("a", "b"))
    assert not class_matches("Navigator firefox_firefox", None)


def test_handover_hides_and_restores_launcher(qt_app, tmp_path):
    config = make_config(tmp_path, [sys.executable, "-c", FAKE_WINDOW])
    handover = Handover(config)
    launcher = FakeLauncherWindow()
    handover.set_launcher_window(launcher)
    events = []
    handover.externalActive.connect(lambda item: events.append(("active", item)))
    handover.externalClosed.connect(lambda item: events.append(("closed", item)))
    handover.errorOccurred.connect(lambda message: events.append(("error", message)))

    try:
        handover.start("target")
        assert pump(handover, 10, lambda: ("active", "target") in events)
        assert launcher.lowered == 1
        assert launcher.visible is True

        handover._process.terminate()
        assert pump(handover, 10, lambda: ("closed", "target") in events)
        assert launcher.raised == 1
        assert launcher.activations == 1
        assert not [event for event in events if event[0] == "error"]
    finally:
        if handover._process and handover._process.poll() is None:
            handover._process.terminate()
        handover._timer.stop()


def test_handover_reports_early_exit(qt_app, tmp_path):
    config = make_config(tmp_path, [sys.executable, "-c", "pass"])
    handover = Handover(config)
    handover.set_launcher_window(FakeLauncherWindow())
    errors = []
    handover.errorOccurred.connect(errors.append)

    try:
        handover.start("target")
        assert pump(handover, 6, lambda: bool(errors))
        assert "avslutades" in errors[0]
        assert handover._item is None
    finally:
        handover._timer.stop()


def test_handover_reports_timeout(qt_app, tmp_path):
    config = make_config(tmp_path, [sys.executable, "-c", "import time; time.sleep(20)"], timeout=1000)
    handover = Handover(config)
    handover.set_launcher_window(FakeLauncherWindow())
    errors = []
    handover.errorOccurred.connect(errors.append)

    try:
        handover.start("target")
        assert pump(handover, 5, lambda: bool(errors))
        assert "inget fönster" in errors[0]
        assert handover._process is None or handover._process.poll() is not None
    finally:
        if handover._process and handover._process.poll() is None:
            handover._process.terminate()
        handover._timer.stop()


def test_request_close_escalates_and_restores(qt_app, tmp_path, monkeypatch):
    import mediahub.handover as handover_module

    monkeypatch.setattr(handover_module, "CLOSE_TIMEOUT", 0.4)
    monkeypatch.setattr(handover_module, "KILL_GRACE", 0.3)

    config = make_config(tmp_path, [sys.executable, "-c", FAKE_WINDOW])
    handover = Handover(config)
    launcher = FakeLauncherWindow()
    handover.set_launcher_window(launcher)
    events = []
    handover.externalActive.connect(lambda item: events.append("active"))
    handover.externalClosed.connect(lambda item: events.append("closed"))

    try:
        handover.start("target")
        assert pump(handover, 10, lambda: "active" in events)
        assert handover.busy is True

        handover.request_close()
        assert pump(handover, 10, lambda: "closed" in events)
        assert launcher.visible is True
        assert handover.busy is False
    finally:
        if handover._process and handover._process.poll() is None:
            handover._process.kill()
        handover._timer.stop()

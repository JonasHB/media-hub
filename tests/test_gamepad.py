import sdl2
import pytest
from PySide6.QtCore import QCoreApplication

from mediahub.gamepad import Gamepad, RepeatAxis


@pytest.fixture(scope="module")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def test_repeat_axis_edge_then_repeat():
    axis = RepeatAxis(delay=0.3, interval=0.1)
    assert axis.update(0, 0.0) is None
    assert axis.update(1, 1.0) == 1
    assert axis.update(1, 1.2) is None
    assert axis.update(1, 1.31) == 1
    assert axis.update(1, 1.32) is None
    assert axis.update(1, 1.42) == 1
    assert axis.update(-1, 2.0) == -1
    assert axis.update(-1, 2.31) == -1
    assert axis.update(0, 2.5) is None
    assert axis.update(0, 9.0) is None
    assert axis.update(1, 10.0) == 1


def test_virtual_controller_navigation(qt_app):
    sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER)
    if sdl2.SDL_JoystickAttachVirtual(sdl2.SDL_JOYSTICK_TYPE_GAMECONTROLLER, 6, 16, 0) < 0:
        pytest.skip(f"virtual joysticks unavailable: {sdl2.SDL_GetError().decode()}")

    gamepad = Gamepad()
    events = []
    gamepad.connectedChanged.connect(lambda: events.append(("connected", gamepad.connected)))
    gamepad.navigate.connect(lambda direction: events.append(("nav", direction)))
    gamepad.categoryStep.connect(lambda direction: events.append(("cat", direction)))
    gamepad.selectPressed.connect(lambda: events.append(("select",)))
    gamepad.backPressed.connect(lambda: events.append(("back",)))
    gamepad.systemMenuPressed.connect(lambda: events.append(("menu",)))

    try:
        gamepad._poll()
        assert ("connected", True) in events

        joystick = sdl2.SDL_JoystickOpen(0)

        sdl2.SDL_JoystickSetVirtualButton(joystick, 0, 1)
        gamepad._poll()
        sdl2.SDL_JoystickSetVirtualButton(joystick, 0, 0)
        gamepad._poll()
        assert events.count(("select",)) == 1, "held button must not auto-repeat"

        sdl2.SDL_JoystickSetVirtualButton(joystick, 1, 1)
        gamepad._poll()
        assert events.count(("back",)) == 1
        sdl2.SDL_JoystickSetVirtualButton(joystick, 1, 0)
        gamepad._poll()

        sdl2.SDL_JoystickSetVirtualButton(joystick, 4, 1)
        gamepad._poll()
        assert events.count(("menu",)) == 1, "Select must open the system menu"

        sdl2.SDL_JoystickSetVirtualAxis(joystick, 0, 30000)
        gamepad._poll()
        assert ("nav", 1) in events

        sdl2.SDL_JoystickSetVirtualAxis(joystick, 0, 0)
        sdl2.SDL_JoystickSetVirtualAxis(joystick, 1, -30000)
        gamepad._poll()
        assert ("cat", -1) in events

        sdl2.SDL_JoystickSetVirtualButton(joystick, 9, 1)
        gamepad._poll()
        assert ("cat", -1) in events
        sdl2.SDL_JoystickSetVirtualButton(joystick, 10, 1)
        gamepad._poll()
        assert ("cat", 1) in events

        sdl2.SDL_JoystickDetachVirtual(0)
        gamepad._poll()
        assert events[-1] == ("connected", False)
    finally:
        gamepad.shutdown()


def test_exit_combo_and_guide_while_suspended(qt_app):
    sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER)
    if sdl2.SDL_JoystickAttachVirtual(sdl2.SDL_JOYSTICK_TYPE_GAMECONTROLLER, 6, 16, 0) < 0:
        pytest.skip("virtual joysticks unavailable")

    gamepad = Gamepad(exit_combo=["left_shoulder", "right_shoulder"])
    events = []
    gamepad.exitComboPressed.connect(lambda: events.append("combo"))
    gamepad.guidePressed.connect(lambda: events.append("guide"))
    gamepad.selectPressed.connect(lambda: events.append("select"))

    try:
        gamepad._poll()
        joystick = sdl2.SDL_JoystickOpen(0)

        sdl2.SDL_JoystickSetVirtualButton(joystick, 9, 1)
        gamepad._poll()
        assert "combo" not in events
        sdl2.SDL_JoystickSetVirtualButton(joystick, 10, 1)
        gamepad._poll()
        assert events.count("combo") == 1
        gamepad._poll()
        assert events.count("combo") == 1

        sdl2.SDL_JoystickSetVirtualButton(joystick, 10, 0)
        gamepad._poll()
        sdl2.SDL_JoystickSetVirtualButton(joystick, 10, 1)
        gamepad._poll()
        assert events.count("combo") == 2

        gamepad.setActive(False)
        sdl2.SDL_JoystickSetVirtualButton(joystick, 0, 1)
        gamepad._poll()
        assert "select" not in events
        sdl2.SDL_JoystickSetVirtualButton(joystick, 5, 1)
        gamepad._poll()
        assert "guide" in events

        sdl2.SDL_JoystickDetachVirtual(0)
        gamepad._poll()
    finally:
        gamepad.shutdown()

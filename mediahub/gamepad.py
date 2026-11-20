from __future__ import annotations

import ctypes
import logging
import time

import sdl2
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

log = logging.getLogger(__name__)

DEADZONE_ENTER = 12000
DEADZONE_EXIT = 8000
REPEAT_DELAY = 0.35
REPEAT_INTERVAL = 0.12
POLL_INTERVAL_MS = 16
RESCAN_INTERVAL = 0.5

BUTTONS = {
    "a": sdl2.SDL_CONTROLLER_BUTTON_A,
    "b": sdl2.SDL_CONTROLLER_BUTTON_B,
    "x": sdl2.SDL_CONTROLLER_BUTTON_X,
    "y": sdl2.SDL_CONTROLLER_BUTTON_Y,
    "back": sdl2.SDL_CONTROLLER_BUTTON_BACK,
    "start": sdl2.SDL_CONTROLLER_BUTTON_START,
    "guide": sdl2.SDL_CONTROLLER_BUTTON_GUIDE,
    "left_shoulder": sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER,
    "right_shoulder": sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER,
    "left_stick": sdl2.SDL_CONTROLLER_BUTTON_LEFTSTICK,
    "right_stick": sdl2.SDL_CONTROLLER_BUTTON_RIGHTSTICK,
}


class RepeatAxis:
    def __init__(self, delay: float = REPEAT_DELAY, interval: float = REPEAT_INTERVAL) -> None:
        self._delay = delay
        self._interval = interval
        self._direction = 0
        self._next_repeat = 0.0

    def update(self, direction: int, now: float) -> int | None:
        if direction == 0:
            self._direction = 0
            return None
        if direction != self._direction:
            self._direction = direction
            self._next_repeat = now + self._delay
            return direction
        if now >= self._next_repeat:
            self._next_repeat = now + self._interval
            return direction
        return None


class Gamepad(QObject):
    navigate = Signal(int)
    verticalStep = Signal(int)
    categoryStep = Signal(int)
    selectPressed = Signal()
    backPressed = Signal()
    systemMenuPressed = Signal()
    guidePressed = Signal()
    screensaverPressed = Signal()
    exitComboPressed = Signal()
    connectedChanged = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        exit_combo: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._exit_combo = list(exit_combo or ["left_shoulder", "right_shoulder"])
        self._combo_active = False
        self._controller = None
        self._controller_name = ""
        self._button_state = {name: False for name in BUTTONS}
        self._stick_direction = {"x": 0, "y": 0}
        self._axis_x = RepeatAxis()
        self._axis_y = RepeatAxis()
        self._next_scan = 0.0
        self._active = True
        self._right_stick_navigation = False

        if sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER) != 0:
            log.error("SDL game controller init failed: %s", sdl2.SDL_GetError().decode())
            return

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._controller is not None

    @Property(str, notify=connectedChanged)
    def controllerName(self) -> str:
        return self._controller_name

    @Slot(bool)
    def setActive(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        self._button_state = {name: False for name in BUTTONS}
        self._combo_active = False
        self._stick_direction = {"x": 0, "y": 0}
        self._axis_x = RepeatAxis()
        self._axis_y = RepeatAxis()
        log.info("gamepad input %s", "enabled" if active else "suspended")

    def _open_controller(self) -> bool:
        for index in range(sdl2.SDL_NumJoysticks()):
            if not sdl2.SDL_IsGameController(index):
                continue
            controller = sdl2.SDL_GameControllerOpen(index)
            if not controller:
                log.warning("could not open controller %d: %s", index, sdl2.SDL_GetError().decode())
                continue
            name = sdl2.SDL_GameControllerName(controller)
            self._controller = controller
            self._controller_name = name.decode() if name else "unknown"
            log.info("gamepad connected: %s", self._controller_name)
            self.connectedChanged.emit()
            return True
        return False

    def _close_controller(self, reason: str) -> None:
        if self._controller is None:
            return
        sdl2.SDL_GameControllerClose(self._controller)
        self._controller = None
        self._controller_name = ""
        self._button_state = {name: False for name in BUTTONS}
        self._stick_direction = {"x": 0, "y": 0}
        self._axis_x = RepeatAxis()
        self._axis_y = RepeatAxis()
        log.info("gamepad disconnected (%s)", reason)
        self.connectedChanged.emit()

    def _poll(self) -> None:
        now = time.monotonic()
        sdl2.SDL_PumpEvents()

        if self._controller is None:
            if now >= self._next_scan:
                self._next_scan = now + RESCAN_INTERVAL
                self._open_controller()
            return

        if sdl2.SDL_GameControllerGetAttached(self._controller) == 0:
            self._close_controller("device removed")
            return

        if self._active:
            self._poll_axes(now)
        self._poll_buttons()

    def _stick(self, axis_name: str, raw: int) -> int:
        current = self._stick_direction.get(axis_name, 0)
        threshold = DEADZONE_EXIT if current != 0 else DEADZONE_ENTER
        if abs(raw) < threshold:
            direction = 0
        else:
            direction = 1 if raw > 0 else -1
        self._stick_direction[axis_name] = direction
        return direction

    def _dpad_axis(self, negative: int, positive: int) -> int:
        return int(self._button_pressed(positive)) - int(self._button_pressed(negative))

    def _button_pressed(self, button: int) -> bool:
        return sdl2.SDL_GameControllerGetButton(self._controller, button) == 1

    @Slot(bool)
    def setRightStickNavigation(self, enabled: bool) -> None:
        self._right_stick_navigation = enabled
        self._stick_direction.pop("rx", None)
        self._stick_direction.pop("ry", None)

    def _poll_axes(self, now: float) -> None:
        x = self._dpad_axis(sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT, sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT)
        if x == 0:
            x = self._stick("x", sdl2.SDL_GameControllerGetAxis(self._controller, sdl2.SDL_CONTROLLER_AXIS_LEFTX))
        if x == 0 and self._right_stick_navigation:
            x = self._stick("rx", sdl2.SDL_GameControllerGetAxis(self._controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTX))

        y = self._dpad_axis(sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP, sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN)
        if y == 0:
            y = self._stick("y", sdl2.SDL_GameControllerGetAxis(self._controller, sdl2.SDL_CONTROLLER_AXIS_LEFTY))
        if y == 0 and self._right_stick_navigation:
            y = self._stick("ry", sdl2.SDL_GameControllerGetAxis(self._controller, sdl2.SDL_CONTROLLER_AXIS_RIGHTY))

        step = self._axis_x.update(x, now)
        if step is not None:
            self.navigate.emit(step)

        step = self._axis_y.update(y, now)
        if step is not None:
            self.verticalStep.emit(step)

    def _poll_buttons(self) -> None:
        actions = {
            "a": self.selectPressed.emit,
            "b": self.backPressed.emit,
            "left_shoulder": lambda: self.categoryStep.emit(-1),
            "right_shoulder": lambda: self.categoryStep.emit(1),
            "start": self.systemMenuPressed.emit,
            "back": self.systemMenuPressed.emit,
            "y": self.screensaverPressed.emit,
        }

        for name, button in BUTTONS.items():
            pressed = self._button_pressed(button)
            if pressed and not self._button_state[name]:
                if name == "guide":
                    self.guidePressed.emit()
                elif self._active and name in actions:
                    actions[name]()
            self._button_state[name] = pressed

        combo_down = all(self._button_state.get(name, False) for name in self._exit_combo)
        if combo_down and not self._combo_active:
            self.exitComboPressed.emit()
        self._combo_active = combo_down

    def shutdown(self) -> None:
        if getattr(self, "_timer", None) is not None:
            self._timer.stop()
        self._close_controller("shutdown")
        sdl2.SDL_QuitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER)

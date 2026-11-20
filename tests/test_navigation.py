import os
import subprocess
import sys
from pathlib import Path


def test_console_navigation(tmp_path):
    (tmp_path / "Harvest Moon.sfc").touch()
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", """
import json
import sys
from pathlib import Path
import sdl2
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from mediahub.config import load_config
from mediahub.gamepad import Gamepad
from mediahub.handover import Handover
from mediahub.library import apply_library
from mediahub.system import SystemActions

config = load_config('config/example.json')
config['categories'][1]['subcategories'].extend([
    {'id': 'wii', 'title': 'Wii', 'items': []},
    {'id': 'other', 'title': 'Other', 'items': []},
])
config['emulators'][0]['rom_dirs'] = [sys.argv[1]]
assert apply_library(config) == []
app = QGuiApplication([])
engine = QQmlApplicationEngine()
gamepad = Gamepad(engine, config['settings']['exit_combo'])
joystick_index = sdl2.SDL_JoystickAttachVirtual(sdl2.SDL_JOYSTICK_TYPE_GAMECONTROLLER, 6, 16, 0)
assert joystick_index >= 0
joystick = sdl2.SDL_JoystickOpen(joystick_index)
gamepad._poll()
assert gamepad.connected
photos = []
for name in ('first', 'second', 'third'):
    path = Path(sys.argv[1]) / (name + '.png')
    image = QImage(16, 16, QImage.Format_RGB32)
    image.fill(0)
    assert image.save(str(path))
    photos.append(path.as_uri())
config['settings']['screensaver'].update(enabled=True, order='sequential', photo_seconds=10)
values = dict(configJson=json.dumps(config), startWindowed=True, windowWidth=800,
              windowHeight=450, slideshowPhotos=json.dumps(photos), screenshotPath='', screenshotDelay=0,
              launcher=Handover(config, engine), systemActions=SystemActions(app), gamepad=gamepad)
for key, value in values.items():
    engine.rootContext().setContextProperty(key, value)
engine.load(QUrl.fromLocalFile('qml/Main.qml'))
window = engine.rootObjects()[0]
QTest.qWait(50)
def image_for(parent, name):
    for child in parent.childItems():
        source = child.property('source')
        if isinstance(source, QUrl) and source.fileName() == name:
            return child
        found = image_for(child, name)
        if found is not None:
            return found

for name in ('prime-video.svg', 'svt-play.svg'):
    image = image_for(window.contentItem(), name)
    assert image is not None
    assert image.property('sourceSize').width() >= image.width() * 2

QTest.keyClick(window, Qt.Key_PageDown)
items = window.property('currentItems').toVariant()
for item, logo in zip(items[1:], ['snes.svg', 'nes.svg', 'wii.svg', 'folder.svg'], strict=True):
    assert item['section']
    url = item['icon']
    assert url.fileName() == logo and not QImage(url.toLocalFile()).isNull()
QTest.keyClick(window, Qt.Key_Right)
QTest.keyClick(window, Qt.Key_Return)
assert window.property('sectionTitle') == 'Super Nintendo'
assert [item['title'] for item in window.property('currentItems').toVariant()] == ['Harvest Moon', 'Tillbaka']
arrow = image_for(window.contentItem(), 'back-arrow.svg')
assert arrow is not None and arrow.isVisible()
button = arrow.parentItem()
assert button.width() == button.height() and button.property('radius') == button.width() / 2
QTest.keyClick(window, Qt.Key_Right)
QTest.keyClick(window, Qt.Key_Return)
assert window.property('sectionTitle') == ''
QTest.keyClick(window, Qt.Key_Return)
assert window.property('sectionTitle') == 'Super Nintendo'
gamepad.backPressed.emit()
assert window.property('sectionTitle') == ''
QTest.keyClick(window, Qt.Key_Right)
QTest.keyClick(window, Qt.Key_Return)
assert window.property('sectionTitle') == 'Nintendo 8-bit'
QTest.keyClick(window, Qt.Key_Escape)
assert window.property('sectionTitle') == ''
slideshow = next(child for child in window.contentItem().childItems()
                 if child.metaObject().indexOfProperty('currentName') >= 0)

def press(button):
    assert sdl2.SDL_JoystickSetVirtualButton(joystick, button, 1) == 0
    gamepad._poll()
    assert sdl2.SDL_JoystickSetVirtualButton(joystick, button, 0) == 0
    gamepad._poll()

def tilt(axis, direction):
    assert sdl2.SDL_JoystickSetVirtualAxis(joystick, axis, direction * 30000) == 0
    gamepad._poll()
    assert sdl2.SDL_JoystickSetVirtualAxis(joystick, axis, 0) == 0
    gamepad._poll()

press(sdl2.SDL_CONTROLLER_BUTTON_Y)
assert slideshow.property('currentName') == 'first'
for control, expected in (
    (lambda: press(sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT), 'third'),
    (lambda: press(sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT), 'first'),
    (lambda: press(sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER), 'second'),
    (lambda: press(sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER), 'first'),
    (lambda: tilt(sdl2.SDL_CONTROLLER_AXIS_LEFTX, 1), 'second'),
    (lambda: tilt(sdl2.SDL_CONTROLLER_AXIS_RIGHTX, -1), 'first'),
):
    control()
    assert slideshow.property('active')
    assert slideshow.property('currentName') == expected
press(sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP)
assert slideshow.property('displaySeconds') == 11
tilt(sdl2.SDL_CONTROLLER_AXIS_RIGHTY, 1)
assert slideshow.property('displaySeconds') == 10
assert slideshow.property('currentName') == 'first'
press(sdl2.SDL_CONTROLLER_BUTTON_B)
assert not slideshow.property('active')
sdl2.SDL_JoystickClose(joystick)
sdl2.SDL_JoystickDetachVirtual(joystick_index)
gamepad.shutdown()
""", str(tmp_path)], cwd=root, env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software"},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr

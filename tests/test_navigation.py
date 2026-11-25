import os
import subprocess
import sys
from pathlib import Path


def test_console_navigation(tmp_path):
    (tmp_path / "Harvest Moon.sfc").touch()
    for index in range(12):
        (tmp_path / f"Test Game {index:02}.sfc").touch()
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-c", """
import json
import os
import sys
from pathlib import Path
import sdl2
from PySide6.QtCore import QPoint, Qt, QUrl
from mediahub.photos import PhotoLibrary
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
from mediahub.steam import SteamGame, apply_steam_library

config = load_config('config/example.json')
assert [item['id'] for item in config['categories'][0]['items']] == [
    'youtube', 'netflix', 'svt-play', 'disney-plus', 'prime-video'
]
assert config['settings']['startup_tile'] == 'svt-play'
config['categories'][1]['subcategories'].extend([
    {'id': 'wii', 'title': 'Wii', 'items': []},
    {'id': 'other', 'title': 'Other', 'items': []},
    {'id': 'steam', 'title': 'Steam', 'items': []},
])
apply_steam_library(config, [SteamGame('413150', 'Stardew Valley')], 'steam')

class Profiles:
    def supports(self, window_class):
        return window_class == 'Stardew Valley'
    def choices(self):
        return [('mouse.gamecontroller.amgp', 'Musprofil')]

selections = Path(sys.argv[1]) / 'selections.json'
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
for name in ('first', 'second'):
    path = Path(sys.argv[1]) / (name + '.png')
    image = QImage(16, 16, QImage.Format_RGB32)
    image.fill(0)
    assert image.save(str(path))

config['settings']['screensaver'].update(enabled=True, order='sequential', photo_seconds=10, folders=[sys.argv[1]])
values = dict(configJson=json.dumps(config), startWindowed=True, windowWidth=800,
              windowHeight=450, photoLibrary=PhotoLibrary([sys.argv[1]], engine), screenshotPath='', screenshotDelay=0,
              launcher=Handover(config, engine, steam_profiles=Profiles(), selections_path=selections), systemActions=SystemActions(app), gamepad=gamepad)
for key, value in values.items():
    engine.rootContext().setContextProperty(key, value)
engine.load(QUrl.fromLocalFile('qml/Main.qml'))
window = engine.rootObjects()[0]
QTest.qWait(50)
assert window.property('selectedTile').toVariant()['id'] == 'svt-play'
QTest.keyClick(window, Qt.Key_Right)
assert window.property('selectedTile').toVariant()['id'] == 'disney-plus'
QTest.keyClick(window, Qt.Key_Left)
QTest.keyClick(window, Qt.Key_Left)
assert window.property('selectedTile').toVariant()['id'] == 'netflix'
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
for item, logo in zip(items[1:], ['snes.svg', 'nes.svg', 'wii.svg', 'folder.svg', 'steam.svg'], strict=True):
    assert item['section']
    url = item['icon']
    assert url.fileName() == logo and not QImage(url.toLocalFile()).isNull()
QTest.keyClick(window, Qt.Key_Right)
QTest.keyClick(window, Qt.Key_Return)
assert window.property('sectionTitle') == 'Super Nintendo'
titles = [item['title'] for item in window.property('currentItems').toVariant()]
assert titles == ['Harvest Moon', *(f'Test Game {i:02}' for i in range(12)), 'Tillbaka']
for direction, expected in [(1, 1), (1, 2), (-1, 1), (-1, 0)]:
    gamepad.navigate.emit(direction)
    QTest.qWait(50)
    QTest.mouseMove(window, QPoint(340, 225))
    QTest.mouseMove(window, QPoint(560, 225))
    QTest.qWait(300)
    assert window.property('tileIndexes').toVariant().get('snes', 0) == expected
arrow = image_for(window.contentItem(), 'back-arrow.svg')
assert arrow is not None and arrow.isVisible()
button = arrow.parentItem()
assert button.width() == button.height() and button.property('radius') == button.width() / 2
QTest.keyClick(window, Qt.Key_Left)
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
QTest.keyClick(window, Qt.Key_Right)
QTest.keyClick(window, Qt.Key_Right)
QTest.keyClick(window, Qt.Key_Right)
QTest.keyClick(window, Qt.Key_Return)
assert window.property('sectionTitle') == 'Steam'
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

press(sdl2.SDL_CONTROLLER_BUTTON_X)
menu = window.findChild(type(window.contentItem()), 'controllerProfileMenu')
assert menu is not None and menu.isVisible()
press(sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN)
press(sdl2.SDL_CONTROLLER_BUTTON_A)
assert not menu.isVisible()
assert json.loads(selections.read_text()) == {'413150': 'mouse.gamecontroller.amgp'}
press(sdl2.SDL_CONTROLLER_BUTTON_X)
assert menu.property('index') == 1
press(sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP)
press(sdl2.SDL_CONTROLLER_BUTTON_A)
assert json.loads(selections.read_text()) == {}

assert QImage(str(Path(sys.argv[1]) / 'first.png')).save(str(Path(sys.argv[1]) / 'third.png'))
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
assert slideshow.property('displaySeconds') == 10.5
tilt(sdl2.SDL_CONTROLLER_AXIS_RIGHTY, 1)
assert slideshow.property('displaySeconds') == 10
feedback = next(child for child in slideshow.childItems()
                if child.objectName() == 'durationFeedback')
assert feedback.property('text') == '10.0s' and feedback.opacity() == 1
press(sdl2.SDL_CONTROLLER_BUTTON_A)
assert slideshow.property('paused') and slideshow.property('active')
for _ in range(20):
    press(sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN)
assert slideshow.property('displaySeconds') == 0.5
assert feedback.property('text') == '0.5s'
if screenshot := os.environ.get('SLIDESHOW_TEST_SCREENSHOT'):
    QTest.qWait(100)
    assert window.grabWindow().save(screenshot)
QTest.qWait(1750)
assert slideshow.property('currentName') == 'first' and feedback.opacity() == 1
QTest.qWait(700)
assert feedback.opacity() == 0
press(sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER)
assert slideshow.property('currentName') == 'second' and slideshow.property('paused')
press(sdl2.SDL_CONTROLLER_BUTTON_A)
assert not slideshow.property('paused') and slideshow.property('active')
for _ in range(70):
    if slideshow.property('currentName') == 'third':
        break
    QTest.qWait(20)
assert slideshow.property('currentName') == 'third'
press(sdl2.SDL_CONTROLLER_BUTTON_B)
assert not slideshow.property('active')
sdl2.SDL_JoystickClose(joystick)
sdl2.SDL_JoystickDetachVirtual(joystick_index)
gamepad.shutdown()
""", str(tmp_path)], cwd=root, env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software"},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr

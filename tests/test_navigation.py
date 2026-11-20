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
config['categories'][1]['subcategories'].append({'id': 'other', 'title': 'Other', 'items': []})
config['emulators'][0]['rom_dirs'] = [sys.argv[1]]
assert apply_library(config) == []
app = QGuiApplication([])
engine = QQmlApplicationEngine()
gamepad = Gamepad(engine, config['settings']['exit_combo'])
values = dict(configJson=json.dumps(config), startWindowed=True, windowWidth=800,
              windowHeight=450, slideshowPhotos='[]', screenshotPath='', screenshotDelay=0,
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
for item, logo in zip(items[1:], ['snes.svg', 'nes.svg', 'folder.svg'], strict=True):
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
gamepad.shutdown()
""", str(tmp_path)], cwd=root, env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software"},
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr

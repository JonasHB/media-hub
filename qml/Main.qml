import QtQuick
import QtQuick.Window
import "components"

Window {
    id: root
    visible: true
    visibility: startWindowed ? Window.Windowed : Window.FullScreen
    width: startWindowed ? windowWidth : Screen.width
    height: startWindowed ? windowHeight : Screen.height
    title: "Media Hub"
    color: "#04060b"

    property var cfg: JSON.parse(configJson)
    property var settings: cfg.settings || ({})
    property bool animations: settings.animations !== false
    property string startingTitle: ""
    readonly property bool showPointer: startWindowed
    property int animMs: animations ? 240 : 0
    property int categoryIndex: 0
    property var tileIndexes: ({})
    property var section: null
    property date now: new Date()
    readonly property var currentCategory: cfg.categories[categoryIndex]
    readonly property string sectionTitle: section ? section.title : ""
    readonly property var currentItems: section
        ? section.items.concat([{title: "Tillbaka", back: true}])
        : currentCategory.items.concat((currentCategory.subcategories || []).map(function(child) {
            var asset = ["snes", "nes", "wii"].indexOf(child.id) !== -1 ? child.id : "folder"
            return {title: child.title, subtitle: "Öppna kategori", section: child,
                    icon: Qt.resolvedUrl("assets/" + asset + ".svg")}
        }))
    readonly property real s: Math.min(width / 1280, height / 720)
    readonly property var uiLocale: Qt.locale(settings.language === "en" ? "en_GB" : "sv_SE")
    readonly property color accent: (section && section.theme) || currentCategory.theme || "#4d9dff"
    readonly property var ssCfg: settings.screensaver || ({})
    readonly property var photoList: JSON.parse(slideshowPhotos)
    readonly property bool ssAvailable: ssCfg.enabled !== false && photoList.length > 0
    readonly property var footerHints: gamepad.connected
        ? ["\u2190 \u2192  Bläddra", "LB / RB  Kategori", "A  Starta", "Y  Bildspel",
           section ? "B  Tillbaka" : "Start  Meny"]
        : ["\u2190 \u2192  Bläddra", "PgUp / PgDn  Kategori", "Enter  Starta",
           "S  Bildspel", section ? "Esc  Tillbaka" : "Esc  Meny"]

    function noteActivity() {
        if (idleTimer.running)
            idleTimer.restart()
    }

    function runSystemAction(action) {
        if (action === "resume") {
            systemMenu.close()
            return
        }
        systemMenu.visible = false
        if (action === "quit") {
            systemActions.quit()
            return
        }
        var done = false
        if (action === "suspend")
            done = systemActions.suspend()
        else if (action === "reboot")
            done = systemActions.reboot()
        else if (action === "poweroff")
            done = systemActions.poweroff()
        if (!done)
            toast.show("Kunde inte utföra åtgärden – se loggen")
        keyLayer.forceActiveFocus()
    }

    function startSlideshow() {
        if (ssCfg.enabled === false) {
            toast.show("Skärmsläckaren är avstängd i konfigurationen")
            return
        }
        if (photoList.length === 0) {
            toast.show("Inga foton hittades – kontrollera screensaver.folders")
            return
        }
        slideshow.begin()
    }

    function selectionKey() {
        return section ? section.id : currentCategory.id
    }

    function tileIndexFor() {
        var idx = tileIndexes[selectionKey()]
        return typeof idx === "number" && idx >= 0 && idx < currentItems.length ? idx : 0
    }

    function setTileIndex(index) {
        var copy = Object.assign({}, tileIndexes)
        copy[selectionKey()] = index
        tileIndexes = copy
    }

    function centerSelection() {
        Qt.callLater(function() { tileList.centerOn(root.tileIndexFor()) })
    }

    function goBack() {
        if (slideshow.active) {
            slideshow.wake()
            return true
        }
        if (!section || launcher.busy)
            return false
        noteActivity()
        section = null
        centerSelection()
        return true
    }

    function selectCategory(index) {
        if (slideshow.active) {
            slideshow.wake()
            return
        }
        noteActivity()
        section = null
        categoryIndex = index
        centerSelection()
    }

    function moveTile(delta) {
        if (slideshow.active) {
            slideshow.wake()
            return
        }
        noteActivity()
        var count = currentItems.length
        if (count === 0)
            return
        var next = (tileIndexFor() + delta + count) % count
        setTileIndex(next)
        Qt.callLater(function() { tileList.centerOn(next) })
    }

    function changeCategory(delta) {
        var count = cfg.categories.length
        selectCategory((categoryIndex + delta + count) % count)
    }

    function activate(index) {
        if (slideshow.active) {
            slideshow.wake()
            return
        }
        noteActivity()
        if (launcher.busy)
            return
        if (typeof index === "number")
            setTileIndex(index)
        var items = currentItems
        var idx = typeof index === "number" ? index : tileIndexFor()
        if (idx >= 0 && idx < items.length) {
            var item = items[idx]
            if (item.section) {
                section = item.section
                centerSelection()
            } else if (item.back) {
                goBack()
            } else {
                startingTitle = item.title
                launcher.start(item.id)
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b1324" }
            GradientStop { position: 0.55; color: "#070b15" }
            GradientStop { position: 1.0; color: "#04060b" }
        }
    }

    SparkField {
        anchors.fill: parent
        s: root.s
        running: root.animations && !slideshow.active && !launcher.busy
        sparkCount: settings.fps === 30 ? 12 : 22
    }

    FocusScope {
        id: keyLayer
        anchors.fill: parent
        focus: true

        Keys.onPressed: function(event) {
            root.noteActivity()
            if (event.key === Qt.Key_S && !slideshow.active) {
                root.startSlideshow()
                event.accepted = true
            } else if (event.key === Qt.Key_PageUp) {
                root.changeCategory(-1)
                event.accepted = true
            } else if (event.key === Qt.Key_PageDown) {
                root.changeCategory(1)
                event.accepted = true
            }
        }
        Keys.onLeftPressed: root.moveTile(-1)
        Keys.onRightPressed: root.moveTile(1)
        Keys.onReturnPressed: root.activate()
        Keys.onEnterPressed: root.activate()
        Keys.onEscapePressed: {
            if (!root.goBack())
                systemMenu.open()
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
            cursorShape: root.showPointer ? Qt.ArrowCursor : Qt.BlankCursor
            onPositionChanged: root.noteActivity()
        }

        Component.onCompleted: {
            keyLayer.forceActiveFocus()
            root.centerSelection()
        }

        Item {
            id: header
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 30 * root.s
            anchors.leftMargin: 56 * root.s
            anchors.rightMargin: 56 * root.s
            height: 86 * root.s

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "MEDIA HUB"
                color: "#46536f"
                font.pixelSize: 18 * root.s
                font.letterSpacing: 4 * root.s
            }

            Row {
                id: categoryBar
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                spacing: 34 * root.s

                Repeater {
                    model: root.cfg.categories
                    delegate: Item {
                        height: 34 * root.s
                        width: catText.implicitWidth

                        Text {
                            id: catText
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.top: parent.top
                            text: modelData.title
                            color: index === root.categoryIndex ? "#ffffff" : "#7c879c"
                            font.pixelSize: 24 * root.s
                            font.letterSpacing: 1 * root.s
                            Behavior on color { ColorAnimation { duration: root.animMs } }
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: catText.implicitWidth
                            height: Math.max(2, 3 * root.s)
                            radius: height / 2
                            color: root.accent
                            opacity: index === root.categoryIndex ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: root.animMs } }
                        }

                        MouseArea {
                            anchors.fill: parent
                            anchors.margins: -8 * root.s
                            hoverEnabled: true
                            cursorShape: root.showPointer ? Qt.PointingHandCursor : Qt.BlankCursor
                            onClicked: root.selectCategory(index)
                        }
                    }
                }
            }

            Column {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2 * root.s

                Text {
                    anchors.right: parent.right
                    text: Qt.formatTime(root.now, "HH:mm")
                    color: "#e9eefb"
                    font.pixelSize: 38 * root.s
                    font.weight: Font.Light
                }

                Text {
                    anchors.right: parent.right
                    text: root.now.toLocaleDateString(root.uiLocale, "dddd d MMMM")
                    color: "#7c879c"
                    font.pixelSize: 16 * root.s
                }
            }
        }

        Item {
            id: content
            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: parent.left
            anchors.right: parent.right

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                text: root.sectionTitle
                visible: root.section !== null
                color: "#e9eefb"
                font.pixelSize: 22 * root.s
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                text: "Inga spel hittades"
                visible: root.section !== null && root.section.items.length === 0
                color: "#7c879c"
                font.pixelSize: 18 * root.s
            }

            Flickable {
                id: tileList
                anchors.centerIn: parent
                width: parent.width
                height: Math.min(430 * root.s, parent.height)
                contentWidth: tilesRow.implicitWidth + 2 * sidePad
                contentHeight: height
                interactive: false
                boundsBehavior: Flickable.StopAtBounds
                clip: true

                readonly property real tileWidth: 220 * root.s
                readonly property real sidePad: tilesRow.implicitWidth <= width
                    ? (width - tilesRow.implicitWidth) / 2
                    : (width - tileWidth) / 2

                Behavior on contentX {
                    enabled: root.animations
                    NumberAnimation { duration: root.animMs; easing.type: Easing.OutCubic }
                }

                function centerOn(index) {
                    var tile = tilesRow.children[index]
                    if (!tile)
                        return
                    var center = tilesRow.x + tile.x + tile.width / 2
                    contentX = Math.max(0, Math.min(center - width / 2, contentWidth - width))
                }

                Row {
                    id: tilesRow
                    x: tileList.sidePad
                    y: (tileList.height - height) / 2
                    spacing: 24 * root.s

                    Repeater {
                        model: root.currentItems
                        delegate: Tile {
                            s: root.s
                            accent: root.accent
                            title: modelData.title
                            subtitle: modelData.subtitle || ""
                            iconSource: modelData.icon || ""
                            folder: !!modelData.section
                            backButton: !!modelData.back
                            focused: index === root.tileIndexFor()
                            showPointer: root.showPointer
                            animations: root.animations
                            animMs: root.animMs
                            onHovered: {
                                root.noteActivity()
                                root.setTileIndex(index)
                            }
                            onActivated: root.activate(index)
                        }
                    }
                }
            }
        }

        Item {
            id: footer
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottomMargin: 22 * root.s
            height: 28 * root.s

            Row {
                anchors.centerIn: parent
                spacing: 40 * root.s

                Repeater {
                    model: root.footerHints
                    delegate: Text {
                        text: modelData
                        color: "#66718a"
                        font.pixelSize: 16 * root.s
                    }
                }
            }
        }

        Toast {
            id: toast
            s: root.s
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: footer.top
            anchors.bottomMargin: 26 * root.s
        }
    }

    Connections {
        target: launcher
        function onErrorOccurred(message) {
            root.startingTitle = ""
            toast.show(message)
        }
        function onExternalActive(itemId) { root.startingTitle = "" }
        function onExternalClosed(itemId) { root.startingTitle = "" }
    }

    Connections {
        target: gamepad
        function onNavigate(direction) {
            if (systemMenu.visible) { systemMenu.move(direction); return }
            if (slideshow.active) { slideshow.wake(); return }
            root.moveTile(direction)
        }
        function onCategoryStep(direction) {
            if (systemMenu.visible) { systemMenu.move(direction); return }
            if (slideshow.active) { slideshow.wake(); return }
            root.changeCategory(direction)
        }
        function onVerticalStep(direction) {
            if (systemMenu.visible) { systemMenu.move(direction); return }
            if (slideshow.active) { slideshow.wake(); return }
        }
        function onSelectPressed() {
            if (systemMenu.visible) { systemMenu.activate(); return }
            if (slideshow.active) { slideshow.wake(); return }
            root.activate()
        }
        function onSystemMenuPressed() {
            if (slideshow.active) { slideshow.wake(); return }
            if (systemMenu.visible)
                systemMenu.close()
            else
                systemMenu.open()
        }
        function onScreensaverPressed() {
            if (slideshow.active) slideshow.wake()
            else root.startSlideshow()
        }
        function onGuidePressed() {
            if (slideshow.active) slideshow.wake()
        }
        function onBackPressed() {
            if (systemMenu.visible) { systemMenu.close(); return }
            root.goBack()
        }
    }

    Slideshow {
        id: slideshow
        anchors.fill: parent
        s: root.s
        photos: root.photoList
        photoSeconds: root.ssCfg.photo_seconds === undefined ? 10 : root.ssCfg.photo_seconds
        transitionMs: root.ssCfg.transition_ms === undefined ? 1200 : root.ssCfg.transition_ms
        kenBurns: root.ssCfg.ken_burns !== false
        order: root.ssCfg.order || "random"
        showFilename: root.ssCfg.show_filename === true
        showPointer: root.showPointer
        dateLocale: root.uiLocale
        onClosed: {
            root.noteActivity()
            keyLayer.forceActiveFocus()
        }
    }

    LaunchOverlay {
        id: launchOverlay
        anchors.fill: parent
        s: root.s
        accent: root.accent
        title: root.startingTitle
        active: root.startingTitle.length > 0 && launcher.busy
    }

    SystemMenu {
        id: systemMenu
        anchors.fill: parent
        s: root.s
        accent: root.accent
        animMs: root.animMs
        onActionChosen: function(action) { root.runSystemAction(action) }
        onClosed: {
            root.noteActivity()
            keyLayer.forceActiveFocus()
        }
    }

    Timer {
        id: idleTimer
        interval: Math.max(1000, (root.ssCfg.idle_seconds === undefined
            ? 300 : root.ssCfg.idle_seconds) * 1000)
        repeat: false
        running: root.ssAvailable
            && (root.ssCfg.idle_seconds === undefined || root.ssCfg.idle_seconds > 0)
            && !launcher.busy
            && !slideshow.active
            && !systemMenu.visible
        onTriggered: root.startSlideshow()
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    Timer {
        interval: screenshotDelay
        running: screenshotPath !== ""
        onTriggered: root.contentItem.grabToImage(function(result) {
            if (result.saveToFile(screenshotPath))
                console.log("media-hub: screenshot saved to " + screenshotPath)
            else
                console.error("media-hub: screenshot failed")
            Qt.quit()
        }, Qt.size(root.width, root.height))
    }
}

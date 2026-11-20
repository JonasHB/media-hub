import QtQuick

FocusScope {
    id: view
    property var photos: []
    property int photoSeconds: 10
    property int transitionMs: 1200
    property bool kenBurns: true
    property string order: "random"
    property bool showFilename: false
    property bool showPointer: true
    property var dateLocale
    property real s: 1
    property bool active: false
    property bool armed: false
    property date now: new Date()

    signal closed()

    visible: active
    focus: active
    z: 200

    property var deck: []
    property int deckIndex: 0
    property bool frontIsA: true
    property int errorCount: 0
    property string currentName: ""

    function shuffled(list) {
        var copy = list.slice()
        for (var i = copy.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1))
            var tmp = copy[i]
            copy[i] = copy[j]
            copy[j] = tmp
        }
        return copy
    }

    function fileName(path) {
        var name = String(path).split("/").pop()
        return name.replace(/\.[^.]+$/, "")
    }

    function buildDeck() {
        deck = order === "sequential" ? photos.slice() : shuffled(photos)
        deckIndex = 0
    }

    function restartKenBurns(layer) {
        kbAnimation.stop()
        layer.scale = 1.0
        kbAnimation.target = layer
        kbAnimation.from = 1.0
        kbAnimation.to = kenBurns ? 1.07 : 1.0
        kbAnimation.duration = photoSeconds * 1000 + transitionMs
        kbAnimation.restart()
    }

    function begin() {
        if (photos.length === 0)
            return
        buildDeck()
        errorCount = 0
        frontIsA = true
        layerA.source = deck[0]
        currentName = fileName(deck[0])
        restartKenBurns(layerA)
        now = new Date()
        active = true
        armed = false
        armTimer.restart()
        forceActiveFocus()
        advanceTimer.restart()
    }

    function wake() {
        if (!active)
            return
        active = false
        advanceTimer.stop()
        kbAnimation.stop()
        layerA.source = ""
        layerB.source = ""
        closed()
    }

    function advance() {
        if (deck.length === 0)
            return
        deckIndex = (deckIndex + 1) % deck.length
        if (deckIndex === 0 && order === "random" && deck.length > 1)
            deck = shuffled(deck)

        var path = deck[deckIndex]
        currentName = fileName(path)
        if (frontIsA) {
            layerB.source = path
            frontIsA = false
            restartKenBurns(layerB)
        } else {
            layerA.source = path
            frontIsA = true
            restartKenBurns(layerA)
        }
        advanceTimer.restart()
    }

    function skipBroken() {
        errorCount += 1
        if (errorCount > deck.length) {
            wake()
            return
        }
        advance()
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
    }

    Image {
        id: layerA
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        smooth: true
        opacity: view.frontIsA ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: view.transitionMs; easing.type: Easing.InOutSine }
        }

        onStatusChanged: {
            if (status === Image.Ready)
                view.errorCount = 0
            else if (status === Image.Error && view.active)
                view.skipBroken()
        }
    }

    Image {
        id: layerB
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        smooth: true
        opacity: view.frontIsA ? 0 : 1

        Behavior on opacity {
            NumberAnimation { duration: view.transitionMs; easing.type: Easing.InOutSine }
        }

        onStatusChanged: {
            if (status === Image.Ready)
                view.errorCount = 0
            else if (status === Image.Error && view.active)
                view.skipBroken()
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 220 * view.s
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 1.0; color: "#66000000" }
        }
    }

    Column {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: 46 * view.s
        spacing: 2 * view.s

        Text {
            anchors.right: parent.right
            text: Qt.formatTime(view.now, "HH:mm")
            color: "#f2f6fd"
            opacity: 0.9
            font.pixelSize: 38 * view.s
            font.weight: Font.Light
        }

        Text {
            anchors.right: parent.right
            text: view.now.toLocaleDateString(
                view.dateLocale || Qt.locale("sv_SE"), "dddd d MMMM")
            color: "#d9e2f0"
            opacity: 0.75
            font.pixelSize: 17 * view.s
        }

        Text {
            anchors.right: parent.right
            visible: view.showFilename && view.currentName.length > 0
            text: view.currentName
            color: "#cfd8e6"
            opacity: 0.55
            font.pixelSize: 14 * view.s
            elide: Text.ElideRight
            width: Math.min(implicitWidth, 420 * view.s)
            horizontalAlignment: Text.AlignRight
        }
    }

    Keys.onPressed: function(event) {
        if (view.armed)
            view.wake()
        event.accepted = true
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.AllButtons
        cursorShape: view.showPointer ? Qt.ArrowCursor : Qt.BlankCursor
        onPositionChanged: if (view.armed) view.wake()
        onClicked: if (view.armed) view.wake()
        onWheel: if (view.armed) view.wake()
    }

    Timer {
        id: armTimer
        interval: 250
        repeat: false
        onTriggered: view.armed = true
    }

    Timer {
        id: advanceTimer
        interval: Math.max(1000, view.photoSeconds * 1000)
        repeat: true
        running: view.active
        onTriggered: view.advance()
    }

    Timer {
        interval: 1000
        repeat: true
        running: view.active
        onTriggered: view.now = new Date()
    }

    PropertyAnimation {
        id: kbAnimation
        property: "scale"
        easing.type: Easing.Linear
    }
}

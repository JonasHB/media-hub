import QtQuick

Item {
    id: overlay

    property real s: 1
    property color accent: "#4d9dff"
    property string title: ""
    property bool active: false
    property bool shown: false

    visible: opacity > 0
    opacity: shown ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: 180 } }

    Rectangle {
        anchors.fill: parent
        color: "#04060b"
    }

    Timer {
        id: armTimer
        interval: 200
        repeat: false
        onTriggered: overlay.shown = true
    }

    onActiveChanged: {
        if (active) {
            armTimer.restart()
        } else {
            armTimer.stop()
            shown = false
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 26 * overlay.s

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 14 * overlay.s

            Repeater {
                model: 3
                delegate: Rectangle {
                    required property int index
                    width: 14 * overlay.s
                    height: width
                    radius: width / 2
                    color: overlay.accent
                    opacity: 0.2

                    SequentialAnimation on opacity {
                        running: overlay.active
                        loops: Animation.Infinite
                        PauseAnimation { duration: index * 160 }
                        NumberAnimation { to: 1.0; duration: 320 }
                        NumberAnimation { to: 0.2; duration: 320 }
                        PauseAnimation { duration: (2 - index) * 160 }
                    }
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: overlay.title.length > 0 ? "Startar " + overlay.title + "\u2026" : "Startar\u2026"
            color: "#e6edf7"
            font.pixelSize: 28 * overlay.s
        }
    }
}

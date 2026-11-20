import QtQuick

Rectangle {
    id: toast
    property string message: ""
    property real s: 1

    width: Math.min(messageText.implicitWidth + 56 * s, 900 * s)
    height: 56 * s
    radius: 14 * s
    color: "#182338"
    border.color: "#3a4a6b"
    border.width: Math.max(1, s)
    opacity: 0
    visible: opacity > 0

    Behavior on opacity { NumberAnimation { duration: 180 } }

    function show(text) {
        message = text
        opacity = 1
        hideTimer.restart()
    }

    Text {
        id: messageText
        anchors.centerIn: parent
        width: Math.min(implicitWidth, 820 * toast.s)
        text: toast.message
        color: "#e7eefc"
        font.pixelSize: 20 * toast.s
        elide: Text.ElideRight
    }

    Timer {
        id: hideTimer
        interval: 4000
        onTriggered: toast.opacity = 0
    }
}

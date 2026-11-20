import QtQuick

Item {
    id: tile
    property string title: ""
    property string subtitle: ""
    property string iconSource: ""
    property bool folder: false
    property bool backButton: false
    property bool focused: false
    property bool animations: true
    property bool showPointer: true
    property int animMs: 240
    property real s: 1
    property color accent: "#4d9dff"

    signal hovered()
    signal activated()

    width: 220 * s
    height: 330 * s
    scale: focused ? 1.08 : 0.96
    opacity: focused ? 1.0 : 0.82

    Behavior on opacity { NumberAnimation { duration: tile.animMs } }

    Behavior on scale {
        enabled: tile.animations
        NumberAnimation { duration: tile.animMs; easing.type: Easing.OutCubic }
    }

    Rectangle {
        visible: !tile.backButton
        anchors.fill: card
        anchors.margins: -10 * tile.s
        radius: 28 * tile.s
        color: tile.accent
        opacity: tile.focused ? 0.18 : 0
        Behavior on opacity { NumberAnimation { duration: tile.animMs } }
    }

    Rectangle {
        id: card
        visible: !tile.backButton
        anchors.fill: parent
        radius: 20 * tile.s
        border.width: tile.focused ? Math.max(2, 2 * tile.s) : Math.max(1, tile.s)
        border.color: tile.focused ? tile.accent : "#20283b"
        gradient: Gradient {
            GradientStop { position: 0.0; color: tile.focused ? "#1d2a44" : "#151c2b" }
            GradientStop { position: 1.0; color: "#0d1220" }
        }

        Behavior on border.color { ColorAnimation { duration: tile.animMs } }

        Item {
            id: iconArea
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 22 * tile.s
            anchors.leftMargin: 20 * tile.s
            anchors.rightMargin: 20 * tile.s
            height: 190 * tile.s

            Image {
                id: icon
                anchors.fill: parent
                source: tile.iconSource
                sourceSize.width: /\.svg$/i.test(tile.iconSource) ? Math.ceil(width * 2) : 0
                asynchronous: true
                fillMode: Image.PreserveAspectFit
                smooth: true
                visible: status === Image.Ready
                onStatusChanged: if (status === Image.Error) source = ""
            }

            Rectangle {
                anchors.centerIn: parent
                width: 124 * tile.s
                height: 124 * tile.s
                radius: 62 * tile.s
                visible: icon.status !== Image.Ready
                gradient: Gradient {
                    GradientStop { position: 0.0; color: tile.accent }
                    GradientStop { position: 1.0; color: Qt.darker(tile.accent, 2.0) }
                }

                Text {
                    anchors.centerIn: parent
                    text: tile.title.length > 0 ? tile.title.charAt(0).toUpperCase() : "?"
                    color: "#eaf2ff"
                    font.pixelSize: 64 * tile.s
                    font.bold: true
                }
            }
        }

        Rectangle {
            visible: tile.folder
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 12 * tile.s
            width: 34 * tile.s
            height: width
            radius: 9 * tile.s
            color: "#0d1220"

            Image {
                anchors.centerIn: parent
                width: 20 * tile.s
                height: width
                source: "../assets/folder.svg"
            }
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 20 * tile.s
            spacing: 4 * tile.s

            Text {
                width: parent.width
                text: tile.title
                color: "#f2f5fb"
                font.pixelSize: 21 * tile.s
                font.bold: true
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                width: parent.width
                text: tile.subtitle
                visible: text.length > 0
                color: "#8e9ab2"
                font.pixelSize: 15 * tile.s
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    Rectangle {
        id: backCircle
        visible: tile.backButton
        anchors.centerIn: parent
        width: 96 * tile.s
        height: width
        radius: width / 2
        color: tile.focused ? Qt.darker(tile.accent, 2.9) : "#151c2b"
        border.color: tile.focused ? tile.accent : "#64728c"
        border.width: Math.max(1, (tile.focused ? 3 : 2) * tile.s)

        Image {
            visible: tile.backButton
            anchors.centerIn: parent
            width: 44 * tile.s
            height: width
            source: tile.backButton ? "../assets/back-arrow.svg" : ""
            sourceSize.width: Math.ceil(width * 2)
        }
    }

    MouseArea {
        anchors.centerIn: parent
        width: tile.backButton ? backCircle.width : tile.width
        height: tile.backButton ? backCircle.height : tile.height
        Accessible.role: Accessible.Button
        Accessible.name: tile.title
        Accessible.onPressAction: tile.activated()
        hoverEnabled: true
        cursorShape: tile.showPointer ? Qt.PointingHandCursor : Qt.BlankCursor
        onEntered: tile.hovered()
        onClicked: tile.activated()
    }
}

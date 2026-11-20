import QtQuick

FocusScope {
    id: menu

    visible: false
    property real s: 1
    property color accent: "#4d9dff"
    property int animMs: 160
    property int index: 0

    signal actionChosen(string action)

    readonly property var entries: [
        { action: "resume", title: "Fortsätt", subtitle: "Tillbaka till menyn" },
        { action: "suspend", title: "Viloläge", subtitle: "Datorn går ner i viloläge" },
        { action: "reboot", title: "Starta om", subtitle: "Startar om datorn" },
        { action: "poweroff", title: "Stäng av", subtitle: "Stänger av datorn" },
        { action: "quit", title: "Stäng launcher", subtitle: "Avsluta Media Hub" }
    ]

    function open() {
        index = 0
        visible = true
        forceActiveFocus()
    }

    function close() {
        visible = false
        closed()
    }

    function move(delta) {
        index = (index + delta + entries.length) % entries.length
    }

    function activate() {
        actionChosen(entries[index].action)
    }

    signal closed()

    Keys.onUpPressed: menu.move(-1)
    Keys.onDownPressed: menu.move(1)
    Keys.onLeftPressed: menu.move(-1)
    Keys.onRightPressed: menu.move(1)
    Keys.onReturnPressed: menu.activate()
    Keys.onEnterPressed: menu.activate()
    Keys.onEscapePressed: menu.close()

    Rectangle {
        anchors.fill: parent
        color: "#04060b"
        opacity: menu.visible ? 0.78 : 0
        Behavior on opacity { NumberAnimation { duration: menu.animMs } }
        MouseArea {
            anchors.fill: parent
            onClicked: menu.close()
        }
    }

    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: 560 * menu.s
        height: content.implicitHeight + 72 * menu.s
        radius: 22 * menu.s
        color: "#0c1420"
        border.width: 1
        border.color: "#22314a"
        opacity: menu.visible ? 1 : 0
        scale: menu.visible ? 1 : 0.96
        Behavior on opacity { NumberAnimation { duration: menu.animMs } }
        Behavior on scale { NumberAnimation { duration: menu.animMs } }

        Column {
            id: content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: 28 * menu.s
            spacing: 8 * menu.s

            Repeater {
                model: menu.entries
                delegate: Item {
                    required property var modelData
                    required property int index
                    width: content.width
                    height: 74 * menu.s

                    Rectangle {
                        anchors.fill: parent
                        radius: 12 * menu.s
                        color: index === menu.index ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: 4 * menu.s
                        height: 40 * menu.s
                        radius: 2 * menu.s
                        color: menu.accent
                        opacity: index === menu.index ? 1 : 0
                    }

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 24 * menu.s
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3 * menu.s

                        Text {
                            text: modelData.title
                            color: index === menu.index ? "#ffffff" : "#c6d2e2"
                            font.pixelSize: 26 * menu.s
                            font.bold: index === menu.index
                        }

                        Text {
                            text: modelData.subtitle
                            color: "#8fa1b8"
                            font.pixelSize: 15 * menu.s
                        }
                    }
                }
            }
        }
    }
}

import QtQuick

Item {
    id: field
    property bool running: true
    property real s: 1
    property int sparkCount: 22

    Image {
        id: warmGlow
        source: "../assets/glow-warm.png"
        width: 1100 * field.s
        height: width
        opacity: 0.5
        smooth: true
        x: field.width * 0.74 - width / 2
        y: field.height * 0.02 - height / 2

        SequentialAnimation on x {
            running: field.running
            loops: Animation.Infinite
            NumberAnimation {
                to: field.width * 0.62 - warmGlow.width / 2
                duration: 52000
                easing.type: Easing.InOutSine
            }
            NumberAnimation {
                to: field.width * 0.8 - warmGlow.width / 2
                duration: 61000
                easing.type: Easing.InOutSine
            }
        }

        SequentialAnimation on y {
            running: field.running
            loops: Animation.Infinite
            NumberAnimation {
                to: field.height * 0.1 - warmGlow.height / 2
                duration: 47000
                easing.type: Easing.InOutSine
            }
            NumberAnimation {
                to: field.height * -0.02 - warmGlow.height / 2
                duration: 57000
                easing.type: Easing.InOutSine
            }
        }
    }

    Image {
        id: coolGlow
        source: "../assets/glow-cool.png"
        width: 1000 * field.s
        height: width
        opacity: 0.42
        smooth: true
        x: field.width * 0.18 - width / 2
        y: field.height * 0.82 - height / 2

        SequentialAnimation on x {
            running: field.running
            loops: Animation.Infinite
            NumberAnimation {
                to: field.width * 0.3 - coolGlow.width / 2
                duration: 63000
                easing.type: Easing.InOutSine
            }
            NumberAnimation {
                to: field.width * 0.12 - coolGlow.width / 2
                duration: 55000
                easing.type: Easing.InOutSine
            }
        }

        SequentialAnimation on y {
            running: field.running
            loops: Animation.Infinite
            NumberAnimation {
                to: field.height * 0.9 - coolGlow.height / 2
                duration: 59000
                easing.type: Easing.InOutSine
            }
            NumberAnimation {
                to: field.height * 0.74 - coolGlow.height / 2
                duration: 67000
                easing.type: Easing.InOutSine
            }
        }
    }

    Image {
        id: amberGlow
        source: "../assets/glow-warm.png"
        width: 760 * field.s
        height: width
        opacity: 0.26
        smooth: true
        x: field.width * 0.32 - width / 2
        y: field.height * 0.72 - height / 2

        SequentialAnimation on x {
            running: field.running
            loops: Animation.Infinite
            NumberAnimation {
                to: field.width * 0.4 - amberGlow.width / 2
                duration: 70000
                easing.type: Easing.InOutSine
            }
            NumberAnimation {
                to: field.width * 0.26 - amberGlow.width / 2
                duration: 64000
                easing.type: Easing.InOutSine
            }
        }
    }

    Repeater {
        model: field.sparkCount

        delegate: Item {
            id: spark
            property int cycleMs: 18000 + Math.floor(Math.random() * 15000)
            property real drift: (30 + Math.random() * 90) * field.s
            property real size: (10 + Math.random() * 22) * field.s

            width: size
            height: size
            x: Math.random() * field.width
            y: field.height * (0.5 + Math.random() * 0.55)
            opacity: 0
            visible: field.running

            Image {
                anchors.fill: parent
                source: "../assets/spark.png"
                smooth: true
            }

            SequentialAnimation on y {
                running: field.running
                loops: Animation.Infinite
                PropertyAction { value: Math.random() * field.height }
                NumberAnimation {
                    to: spark.y - spark.rise
                    duration: spark.cycleMs
                    easing.type: Easing.InOutSine
                }
            }

            SequentialAnimation on x {
                running: field.running
                loops: Animation.Infinite
                NumberAnimation {
                    to: spark.x + spark.drift
                    duration: Math.max(4000, spark.cycleMs / 2)
                    easing.type: Easing.InOutSine
                }
                NumberAnimation {
                    to: spark.x - spark.drift
                    duration: Math.max(4000, spark.cycleMs / 2)
                    easing.type: Easing.InOutSine
                }
            }

            SequentialAnimation on opacity {
                running: field.running
                loops: Animation.Infinite
                NumberAnimation {
                    from: 0
                    to: 0.5 + Math.random() * 0.4
                    duration: spark.cycleMs * 0.35
                    easing.type: Easing.InOutSine
                }
                NumberAnimation {
                    to: 0
                    duration: spark.cycleMs * 0.55
                    easing.type: Easing.InOutSine
                }
                PauseAnimation { duration: spark.cycleMs * 0.1 }
            }
        }
    }
}

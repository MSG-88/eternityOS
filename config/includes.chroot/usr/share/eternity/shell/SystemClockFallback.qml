import QtQuick

// HH:MM from the local clock when the daemon is away (the daemon's clock wins when present).
QtObject {
    id: root
    property string timeText: Qt.formatTime(new Date(), "HH:mm")
    property Timer timer: Timer { interval: 1000; running: true; repeat: true; onTriggered: root.timeText = Qt.formatTime(new Date(), "HH:mm") }
}

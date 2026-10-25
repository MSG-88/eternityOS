pragma Singleton
import QtQuick

// Shared sizes for the Settings controls (design: toggle 38x22, seg 13 px, slider 240x2).
QtObject {
    readonly property int toggleW: 38
    readonly property int toggleH: 22
    readonly property int sliderW: 240
}

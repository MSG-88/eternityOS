pragma Singleton
import QtQuick
import Quickshell

// Shared state of the ask bar. While an answer is on screen the presence slides to the left and
// the answer runs down the right-hand column as plain text (owner's direction, 2026-10-26).
Singleton {
    property bool answering: false
}

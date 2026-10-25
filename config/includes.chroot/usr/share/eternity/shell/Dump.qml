import QtQuick
import Quickshell.Io

// Test support: when ETERNITY_SHELL_DUMP names a directory, write <dir>/dump.json from `payload`
// and grab `target` into <dir>/<name>.png, then quit. Inert when the variable is unset.
Item {
    id: root
    property string dir
    property string name: "shot"
    property Item target
    property var payload: ({})
    property var collect: null      // function evaluated at dump time (after layout), wins over payload
    property bool armed: dir !== ""
    signal done()
    Timer {
        interval: 900; running: root.armed; repeat: false
        onTriggered: {
            const json = JSON.stringify(root.collect ? root.collect() : root.payload);
            writer.command = ["sh", "-c", "printf '%s' \"$1\" > \"$2\"", "dump", json, root.dir + "/dump.json"];
            writer.running = true;
            if (root.target) root.target.grabToImage(function (r) { r.saveToFile(root.dir + "/" + root.name + ".png"); root.done(); quitTimer.start(); });
            else { root.done(); quitTimer.start(); }
        }
    }
    Timer { id: quitTimer; interval: 300; repeat: false; onTriggered: Qt.quit() }
    Process { id: writer }
}

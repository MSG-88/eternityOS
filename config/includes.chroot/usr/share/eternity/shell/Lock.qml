import QtQuick
import Quickshell
import Quickshell.Wayland

// Session lock (ext-session-lock): raised by the daemon's session.lock event (eternity-lock,
// hypridle, Super+L); one LockContent per screen; unlocks when any screen's scene authenticates.
Scope {
    id: root
    property var info: ({})
    WlSessionLock {
        id: lock
        locked: false
        onSecureChanged: { if (secure) Daemon.call("session.locked", {}, null); }
        onLockedChanged: { if (!locked) Daemon.call("session.unlocked", {}, null); }
        surface: Component {
            WlSessionLockSurface {
                color: Theme.bg
                LockContent {
                    anchors.fill: parent
                    k: Geometry.forScreen(screen)
                    info: root.info
                    onUnlocked: lock.locked = false
                }
            }
        }
    }
    function engage() {
        Daemon.call("session.lock_info", {}, (r, e) => { if (r) root.info = r; });
        lock.locked = true;
    }
    Connections { target: Daemon; function onEvent(name, data) { if (name === "session.lock") root.engage(); } }
}

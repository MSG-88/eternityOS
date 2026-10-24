#!/bin/sh
# Put the Eternity 08 launchers on the desktop (XFCE needs them executable and trusted).
# The installer icon appears only in a live session. Runs from /etc/xdg/autostart.
# With the presence shell active (desktop icons style 0) the launchers live in the shell and the radial launcher.
DESKTOP=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
mkdir -p "$DESKTOP"

place() {
    src=/usr/share/applications/$1
    dst=$DESKTOP/$1
    [ -f "$src" ] || return 0
    [ -f "$dst" ] || cp "$src" "$dst"
    chmod +x "$dst"
    if command -v gio >/dev/null 2>&1; then
        gio set --type=string "$dst" metadata::trusted true 2>/dev/null || true
        gio set --type=string "$dst" metadata::xfce-exe-checksum \
            "$(sha256sum "$dst" | cut -d' ' -f1)" 2>/dev/null || true
    fi
}

place eternity-chat.desktop
if [ -d /run/live/medium ]; then
    place eternity-install.desktop
fi
exit 0

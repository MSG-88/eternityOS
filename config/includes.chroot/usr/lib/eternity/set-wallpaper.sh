#!/bin/sh
# Apply the Eternity 08 wallpaper to every connected monitor and workspace once per login.
# Runs from /etc/xdg/autostart/eternity-wallpaper.desktop; idempotent and quick.
WALL=/usr/share/eternity/wallpaper-1920x1080.png
command -v xfconf-query >/dev/null 2>&1 || exit 0
command -v xrandr >/dev/null 2>&1 || exit 0
[ -f "$WALL" ] || exit 0

# Pick the largest wallpaper that is not bigger than the primary screen
res=$(xrandr --current 2>/dev/null | sed -n 's/.* connected.* \([0-9]\+\)x\([0-9]\+\)+.*/\1/p' | sort -n | tail -1)
if [ -n "$res" ]; then
    if [ "$res" -ge 3840 ]; then WALL=/usr/share/eternity/wallpaper-3840x2160.png
    elif [ "$res" -ge 2560 ]; then WALL=/usr/share/eternity/wallpaper-2560x1440.png
    fi
fi

for mon in $(xrandr --listmonitors 2>/dev/null | awk 'NR>1 {print $NF}'); do
    for ws in 0 1 2 3; do
        base="/backdrop/screen0/monitor${mon}/workspace${ws}"
        xfconf-query -c xfce4-desktop -p "$base/last-image" -n -t string -s "$WALL" 2>/dev/null
        xfconf-query -c xfce4-desktop -p "$base/image-style" -n -t int -s 5 2>/dev/null
        xfconf-query -c xfce4-desktop -p "$base/color-style" -n -t int -s 0 2>/dev/null
    done
done
exit 0

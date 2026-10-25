#!/bin/bash
# Feasibility spike (not product code): can Quickshell 0.3 and Hyprland 0.55 from trixie-backports
# be installed on Debian 13 and does Quickshell render QML offscreen? Run as root in WSL.
set -x
grep -q trixie-backports /etc/apt/sources.list.d/*.list /etc/apt/sources.list 2>/dev/null || echo "deb https://deb.debian.org/debian trixie-backports main" > /etc/apt/sources.list.d/backports.list
apt-get update -qq 2>&1 | tail -2
apt-get install -y -qq -t trixie-backports quickshell 2>&1 | tail -3
apt-get install -y -qq qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-layouts qml6-module-qtquick-shapes qml6-module-qtquick-effects qt6-qpa-plugins mesa-utils 2>&1 | tail -2
apt-get install -y -qq --download-only -t trixie-backports hyprland hyprlock hypridle xdg-desktop-portal-hyprland 2>&1 | tail -2
quickshell --version
ls /usr/lib/x86_64-linux-gnu/qt6/plugins/platforms/ | tr '\n' ' '; echo
apt-cache policy hyprland quickshell | grep -E "^[a-z]|Candidate"
dpkg -s quickshell | grep -E "^(Version|Installed-Size)"

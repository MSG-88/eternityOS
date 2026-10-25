#!/bin/bash
# Which packages hyprland + quickshell pull from trixie-backports (dev helper, run as root in WSL).
apt-get update -qq 2>/dev/null
apt-get install -s -y -t trixie-backports hyprland quickshell hypridle xdg-desktop-portal-hyprland 2>/dev/null | grep -E "^Inst " | awk '{print $2, $3, $4}' | grep -i "bpo" | sort
echo "---- versions needed"
apt-cache depends hyprland 2>/dev/null | grep -E "Depends" | head -30 | tr '\n' ' '; echo

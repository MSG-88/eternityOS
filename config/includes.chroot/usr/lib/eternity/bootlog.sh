#!/bin/sh
# Eternity 08 boot log: six real facts about this boot, shown as numbered lines by the
# Plymouth theme while the system comes up (eternity-bootlog.service). Nothing here is
# invented: every line is read from the kernel, firmware or the installed AI stack.
say() {
    plymouth display-message --text="$1" 2>/dev/null || true
    sleep "${ETERNITY_BOOTLOG_PAUSE:-0.35}"
}
plymouth --ping 2>/dev/null || exit 0

kver=$(uname -r)
if [ -d /sys/firmware/efi ]; then
    sb="secure boot off"
    for f in /sys/firmware/efi/efivars/SecureBoot-*; do
        [ -r "$f" ] || continue
        # the last byte of the variable is the state
        [ "$(od -An -tu1 -j4 -N1 "$f" 2>/dev/null | tr -d ' ')" = 1 ] && sb="secure boot verified"
    done
else
    sb="legacy BIOS boot"
fi
say "eternity-kernel $kver  ·  $sb"

threads=$(nproc 2>/dev/null || echo 1)
if command -v llama-cli >/dev/null 2>&1 || command -v llama-completion >/dev/null 2>&1; then
    say "neural runtime  ·  llama.cpp, $threads cores online"
else
    say "neural runtime  ·  not installed"
fi

model=""
for role in default small; do
    f=/opt/eternity/models/$role.gguf
    if [ -f "$f" ]; then
        model=$(basename "$(readlink -f "$f")" .gguf)
        size=$(du -h "$(readlink -f "$f")" 2>/dev/null | cut -f1)
        say "memory graph  ·  $model ($size) staged"
        break
    fi
done
[ -n "$model" ] || say "memory graph  ·  no local model"

sensors=""
[ -e /dev/video0 ] && sensors="camera"
if [ -d /proc/asound ] && ls /proc/asound 2>/dev/null | grep -q '^card'; then sensors="${sensors:+$sensors, }microphone"; fi
[ -d /sys/class/power_supply/BAT0 ] || [ -d /sys/class/power_supply/BAT1 ] && sensors="${sensors:+$sensors, }battery"
say "sensors  ·  ${sensors:-none detected}"

mem=$(awk '/^MemTotal:/ {printf "%.1f GB", $2/1048576}' /proc/meminfo)
say "scheduler  ·  $threads threads, $mem memory"
say "ready"
exit 0

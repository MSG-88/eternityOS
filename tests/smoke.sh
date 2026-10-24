#!/bin/bash
# Eternity 08 in-image self-test.
# Runs as root inside the booted image when the kernel command line contains
# `eternity.test`. Output goes to the serial console (see eternity-smoke.service).
#
# Contract: one line per check  ->  "CHECK <name>: PASS" | "CHECK <name>: FAIL <reason>" | "CHECK <name>: SKIP <reason>"
#           then                 ->  "SMOKE: PASS" | "SMOKE: FAIL"
#           then                 ->  "SMOKE_DONE"
# Every function named check_<name> is run, in sorted order. A check returns 0 (pass),
# 1 (fail), or 2 (skip); anything it prints is appended as the reason.

EXPECT_DIR=/usr/lib/eternity/expect

# Under software-emulated QEMU (TCG, no KVM on the test host) everything runs an order of
# magnitude slower; the model timeouts are stretched by SCALE so the checks stay meaningful.
VIRT=$(systemd-detect-virt 2>/dev/null || echo none)
SCALE=1; [ "$VIRT" = qemu ] && SCALE=${ETERNITY_SMOKE_SCALE:-10}

# Idle memory is sampled here, right after boot, before any check loads a model or
# imports torch; check_memory grades this figure (the spec's budget is idle memory).
USED_AT_BOOT_KB=$(free -k | awk '/^Mem:/ {print $3}')

echo "ETERNITY SMOKE START"
echo "INFO kernel: $(uname -r)"
echo "INFO virt: $VIRT timeout-scale=$SCALE"
echo "INFO cmdline: $(cat /proc/cmdline)"
echo "INFO memory: $(free -k | awk '/^Mem:/ {print "total="$2"kB used="$3"kB available="$7"kB"}')"

check_os_release() {
    # Every expected line must be present verbatim; live-build may add IMAGE_ID/BUILD_ID lines.
    local line
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        grep -qxF -- "$line" /etc/os-release || { echo "missing line: $line"; return 1; }
    done < "$EXPECT_DIR/os-release.txt"
    grep -qE '^(ID=debian|NAME="Debian)' /etc/os-release && { echo "Debian identity still present"; return 1; }
    grep -qxF 'ID=eternity' /usr/lib/os-release || { echo "/usr/lib/os-release not branded"; return 1; }
    return 0
}

check_identity() {
    [ "$(cat /etc/hostname)" = eternity ] || { echo "hostname file is '$(cat /etc/hostname)'"; return 1; }
    grep -q 'Eternity 08' /etc/issue || { echo "/etc/issue lacks Eternity 08"; return 1; }
    [ -s /usr/share/eternity/fastfetch.txt ] || { echo "fastfetch.txt missing"; return 1; }
    fastfetch --logo-type file --logo /usr/share/eternity/fastfetch.txt --pipe >/dev/null 2>&1 || { echo "fastfetch failed"; return 1; }
}

check_assets() {
    local d=/usr/share/eternity f
    for f in logo.svg logo-64.png logo-128.png logo-256.png logo-512.png \
             wallpaper-1920x1080.png wallpaper-2560x1440.png wallpaper-3840x2160.png greeter-1920x1080.png; do
        [ -s "$d/$f" ] || { echo "missing $d/$f"; return 1; }
    done
    file "$d/wallpaper-1920x1080.png" | grep -q '1920 x 1080' || { echo "wallpaper-1920x1080 wrong size"; return 1; }
    file "$d/wallpaper-2560x1440.png" | grep -q '2560 x 1440' || { echo "wallpaper-2560x1440 wrong size"; return 1; }
    file "$d/wallpaper-3840x2160.png" | grep -q '3840 x 2160' || { echo "wallpaper-3840x2160 wrong size"; return 1; }
    file "$d/greeter-1920x1080.png" | grep -q '1920 x 1080' || { echo "greeter wrong size"; return 1; }
    file "$d/logo-512.png" | grep -q '512 x 512' || { echo "logo-512 wrong size"; return 1; }
}

check_desktop() {
    dpkg -s xfce4 >/dev/null 2>&1 || { echo "xfce4 not installed"; return 1; }
    dpkg -s lightdm-gtk-greeter >/dev/null 2>&1 || { echo "lightdm-gtk-greeter not installed"; return 1; }
    grep -q 'Arc-Dark' /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xsettings.xml 2>/dev/null || { echo "xsettings.xml lacks Arc-Dark"; return 1; }
    grep -q 'wallpaper-1920x1080.png' /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml 2>/dev/null || { echo "xfce4-desktop.xml lacks wallpaper"; return 1; }
    grep -q 'whiskermenu' /etc/xdg/xfce4/panel/default.xml 2>/dev/null || { echo "panel default.xml lacks whiskermenu"; return 1; }
    grep -qx 'button-icon=eternity' /etc/xdg/xfce4/panel/whiskermenu-1.rc 2>/dev/null || { echo "whiskermenu rc lacks eternity icon"; return 1; }
    [ -x /usr/lib/eternity/set-wallpaper.sh ] || { echo "set-wallpaper.sh missing or not executable"; return 1; }
    [ -s /usr/share/icons/hicolor/256x256/apps/eternity.png ] || { echo "hicolor eternity icon missing"; return 1; }
    [ -s /usr/share/pixmaps/eternity.png ] || { echo "pixmaps eternity.png missing"; return 1; }
    # Icon caches must exist and be newer than their theme dir, or every GTK process
    # indexes the 43 000 Papirus icons in memory at startup (1.3 GB per session in build 7).
    local t
    for t in Papirus-Dark Papirus hicolor Adwaita; do
        [ -f "/usr/share/icons/$t/icon-theme.cache" ] || { echo "icon-theme.cache missing for $t"; return 1; }
        [ "$(stat -c %Y "/usr/share/icons/$t/icon-theme.cache")" -ge "$(stat -c %Y "/usr/share/icons/$t")" ] \
            || { echo "icon-theme.cache stale for $t"; return 1; }
    done
}

check_boot_theme() {
    [ "$(plymouth-set-default-theme 2>/dev/null)" = eternity ] || { echo "plymouth default theme is '$(plymouth-set-default-theme 2>/dev/null)'"; return 1; }
    [ -s /usr/share/grub/themes/eternity/theme.txt ] || { echo "installed-system GRUB theme missing"; return 1; }
    grep -qs 'Eternity 08' /etc/default/grub.d/eternity.cfg || { echo "grub.d/eternity.cfg lacks Eternity 08"; return 1; }
    local initrd
    initrd=$(ls /boot/initrd.img-* 2>/dev/null | head -1)
    [ -n "$initrd" ] || { echo "no initrd in /boot"; return 1; }
    lsinitramfs "$initrd" 2>/dev/null | grep -q 'plymouth/themes/eternity' || { echo "initrd lacks plymouth eternity theme"; return 1; }
    # Design refresh (2026-10-25): the splash animates the Möbius mark from pre-rendered frames
    # and shows real boot-log lines sent by eternity-bootlog.service.
    lsinitramfs "$initrd" 2>/dev/null | grep -q 'plymouth/themes/eternity/ring-loop-23.png' || { echo "initrd lacks the ring frames"; return 1; }
    [ -x /usr/lib/eternity/bootlog.sh ] || { echo "bootlog.sh missing or not executable"; return 1; }
    [ "$(systemctl is-enabled eternity-bootlog.service 2>/dev/null)" = enabled ] || { echo "eternity-bootlog.service not enabled"; return 1; }
    [ -f /usr/share/fonts/truetype/michroma/Michroma-Regular.ttf ] || { echo "Michroma font missing"; return 1; }
    grep -q '#9184d9' /usr/share/grub/themes/eternity/theme.txt || { echo "GRUB theme is not the Nocturne palette"; return 1; }
}

check_secureboot() {
    [ -d /sys/firmware/efi ] || { echo "not an EFI boot"; return 2; }
    mokutil --sb-state 2>/dev/null | grep -q 'SecureBoot enabled' || { echo "$(mokutil --sb-state 2>&1 | head -1)"; return 1; }
}

check_login() {
    # Live sessions get the hinted greeter image (set by live-config 0031-eternity-user);
    # the image itself, and so every installed system, carries the plain wallpaper.
    if grep -q 'boot=live' /proc/cmdline; then
        grep -qs 'greeter-1920x1080.png' /etc/lightdm/lightdm-gtk-greeter.conf || { echo "live greeter conf lacks the hinted background"; return 1; }
    else
        grep -qs '^background=/usr/share/eternity/wallpaper-1920x1080.png' /etc/lightdm/lightdm-gtk-greeter.conf || { echo "greeter conf lacks the plain wallpaper background"; return 1; }
    fi
    grep -qsx 'autologin-user=' /etc/lightdm/lightdm.conf.d/10-eternity.conf || { echo "10-eternity.conf lacks empty autologin-user"; return 1; }
    [ "$(systemctl is-enabled lightdm 2>/dev/null)" = enabled ] || { echo "lightdm not enabled"; return 1; }
    if grep -qs 'autologin-user=eternity' /etc/lightdm/lightdm.conf.d/*.conf /etc/lightdm/lightdm.conf; then
        echo "live autologin is enabled"; return 1
    fi
    if grep -q 'boot=live' /proc/cmdline; then
        getent passwd eternity >/dev/null || { echo "live user eternity missing"; return 1; }
        # The greeter hint promises password "eternity"; live-config's default is "live".
        local hash
        hash=$(getent shadow eternity | cut -d: -f2)
        perl -e 'exit(crypt($ARGV[0], $ARGV[1]) eq $ARGV[1] ? 0 : 1)' eternity "$hash" \
            || { echo "live password is not 'eternity'"; return 1; }
        getent passwd eternity | cut -d: -f5 | grep -q 'Eternity' \
            || { echo "live user full name is '$(getent passwd eternity | cut -d: -f5)'"; return 1; }
    fi
}

check_memory() {
    # Proxy for the idle figure (no desktop session here): `used` at multi-user must stay under 450 MB.
    grep -q 'boot=live' /proc/cmdline || { echo "not a live boot"; return 2; }
    # Sampled at script start (see USED_AT_BOOT_KB): the checks that run before this one
    # (alphabetical order) load models and torch, which inflated a sample taken here to
    # 488 MB in build 6 while boot-time use was 299 MB.
    [ "$USED_AT_BOOT_KB" -lt 450000 ] || { echo "used ${USED_AT_BOOT_KB}kB at multi-user (sampled at boot), limit 450000kB"; return 1; }
    echo "INFO idle: ${USED_AT_BOOT_KB}kB used at multi-user" >&2
}

check_installer() {
    dpkg -s calamares >/dev/null 2>&1 || { echo "calamares not installed"; return 1; }
    grep -qs 'productName: *Eternity 08' /etc/calamares/branding/eternity/branding.desc || { echo "branding.desc lacks Eternity 08"; return 1; }
    grep -qs '^branding: *eternity' /etc/calamares/settings.conf || { echo "settings.conf does not select eternity branding"; return 1; }
    [ -x /usr/lib/eternity/post-install.sh ] || { echo "post-install.sh missing"; return 1; }
    [ -s /usr/share/applications/eternity-install.desktop ] || { echo "eternity-install.desktop missing"; return 1; }
    # The install must work offline with the GRUB this image ships (grub-*-bin only).
    # Debian's bootloader-config helper would apt-get grub-efi and run update-grub before
    # grub-install created /boot/grub, aborting the install after the disk was wiped.
    grep -qsE '^\s*-\s*(bootloader-config|sources-media)' /etc/calamares/settings.conf \
        && { echo "settings.conf still runs Debian's online bootloader-config/sources-media jobs"; return 1; }
    [ -s /etc/default/grub ] || { echo "/etc/default/grub missing"; return 1; }
    command -v grub-install >/dev/null && command -v update-grub >/dev/null || { echo "grub-install/update-grub missing"; return 1; }
    [ -x /etc/kernel/postinst.d/zz-update-grub ] || { echo "kernel postinst hook zz-update-grub missing"; return 1; }
    dpkg -s mate-polkit >/dev/null 2>&1 || { echo "no polkit agent (mate-polkit) for pkexec calamares"; return 1; }
    # EFI fallback: Calamares must not copy the bare signed GRUB to EFI/boot (grub> prompt);
    # post-install.sh installs shim+GRUB+grub.cfg there instead when Windows does not own it.
    grep -qsE '^installEFIFallback: *false' /etc/calamares/modules/bootloader.conf || { echo "bootloader.conf does not set installEFIFallback: false"; return 1; }
    grep -qsE '^efiBootloaderId: *"Eternity_08"' /etc/calamares/modules/bootloader.conf || { echo "bootloader.conf lacks efiBootloaderId Eternity_08"; return 1; }
    grep -qs -- '--force-extra-removable' /usr/lib/eternity/post-install.sh || { echo "post-install.sh does not install the removable fallback loader"; return 1; }
    grep -qs 'EFI/BOOT/grub.cfg' /usr/lib/eternity/post-install.sh || { echo "post-install.sh does not copy grub.cfg to EFI/BOOT"; return 1; }
}

check_security() {
    # Backlog item 2: firewall default-deny inbound, AppArmor, unattended security updates, sysctl hardening.
    [ -s /etc/nftables.conf ] || { echo "/etc/nftables.conf missing"; return 1; }
    grep -q 'policy drop' /etc/nftables.conf || { echo "nftables input policy is not drop"; return 1; }
    [ "$(systemctl is-enabled nftables 2>/dev/null)" = enabled ] || { echo "nftables.service not enabled"; return 1; }
    if command -v nft >/dev/null 2>&1 && systemctl is-active nftables >/dev/null 2>&1; then
        nft list chain inet filter input 2>/dev/null | grep -q 'policy drop' || { echo "live ruleset has no drop policy on input"; return 1; }
    fi
    [ "$(cat /sys/module/apparmor/parameters/enabled 2>/dev/null)" = Y ] || { echo "AppArmor not enabled in the kernel"; return 1; }
    [ "$(systemctl is-enabled apparmor 2>/dev/null)" = enabled ] || { echo "apparmor.service not enabled"; return 1; }
    [ -s /etc/apt/apt.conf.d/52eternity-unattended ] || { echo "unattended-upgrades config missing"; return 1; }
    dpkg -s unattended-upgrades >/dev/null 2>&1 || { echo "unattended-upgrades not installed"; return 1; }
    [ -s /etc/sysctl.d/60-eternity-hardening.conf ] || { echo "sysctl hardening missing"; return 1; }
    [ "$(sysctl -n kernel.yama.ptrace_scope 2>/dev/null)" = 1 ] || { echo "ptrace_scope is not 1"; return 1; }
    ss -H -tln 2>/dev/null | awk '{print $4}' | grep -vE '^(127\.0\.0\.1|\[::1\]|::1):' | grep -q . && { echo "a TCP service listens on a non-loopback address: $(ss -H -tln | awk '{print $4}' | grep -vE '^(127\.0\.0\.1|\[::1\]):' | tr '
' ' ')"; return 1; }
    grep -qs -- 'sudo' /usr/lib/eternity/py/eternity/actions.py || { echo "action broker lacks the no-sudo rule"; return 1; }
    return 0
}

check_venv() {
    local py=/opt/eternity/venv/bin/python
    [ -x "$py" ] || { echo "venv python missing"; return 1; }
    "$py" - <<'PY' 2>&1 | tail -n 3 || return 1
import torch, transformers, sklearn, pandas, numpy, scipy, matplotlib, sentence_transformers, llama_cpp
assert not torch.cuda.is_available()
assert torch.tensor([1.0, 2.0]).sum().item() == 3.0
print("torch", torch.__version__, "transformers", transformers.__version__)
PY
    [ "${PIPESTATUS[0]}" = 0 ] || { echo "venv import test failed"; return 1; }
    [ -x /opt/eternity/venv/bin/jupyter ] || { echo "jupyter missing from venv"; return 1; }
    grep -qs '/opt/eternity/venv/bin' /etc/profile.d/eternity-venv.sh || { echo "profile.d PATH entry missing"; return 1; }
}

check_llama() {
    command -v llama-cli >/dev/null || { echo "llama-cli missing"; return 1; }
    llama-cli --version >/dev/null 2>&1 || { echo "llama-cli --version failed"; return 1; }
    command -v llama-server >/dev/null || { echo "llama-server missing"; return 1; }
    [ -f /etc/systemd/system/llama-server.service ] || { echo "llama-server.service missing"; return 1; }
    [ "$(systemctl is-enabled llama-server 2>/dev/null)" = disabled ] || { echo "llama-server should be disabled, is '$(systemctl is-enabled llama-server 2>/dev/null)'"; return 1; }
    # The shipped unit must actually start llama-server (a bad ExecStart argument would
    # crash-loop it once enabled). Run its ExecStart line here, with the small model so it
    # fits a 4 GB machine and with the unit's Environment= expanded the way systemd does,
    # and wait for the /health endpoint.
    local exec env_line out pid i ok=1
    exec=$(sed -n 's/^ExecStart=//p' /etc/systemd/system/llama-server.service | head -1)
    env_line=$(sed -n 's/^Environment=//p' /etc/systemd/system/llama-server.service | tr '\n' ' ')
    exec=${exec//default.gguf/small.gguf}
    out=$(mktemp)
    ( eval "export $env_line"; eval "exec $exec" ) >"$out" 2>&1 &
    pid=$!
    for i in $(seq 1 $((60 * SCALE))); do
        curl -fs http://127.0.0.1:8080/health >/dev/null 2>&1 && { ok=0; break; }
        kill -0 $pid 2>/dev/null || break
        sleep 2
    done
    kill $pid 2>/dev/null; wait $pid 2>/dev/null
    [ $ok = 0 ] || { echo "llama-server did not come up from the unit's ExecStart: $(tail -c 200 "$out" | tr '\n' ' ')"; rm -f "$out"; return 1; }
    rm -f "$out"
}

check_models() {
    local d=/opt/eternity/models
    [ -f "$d/default.gguf" ] && [ -f "$d/small.gguf" ] || { echo "default.gguf/small.gguf missing"; return 1; }
    [ -s "$d/SHA256SUMS" ] || { echo "SHA256SUMS missing"; return 1; }
    (cd "$d" && sha256sum --quiet -c SHA256SUMS) || { echo "checksum mismatch"; return 1; }
    [ -s "$d/models.json" ] || { echo "models.json missing"; return 1; }
    ls "$d"/*.LICENSE >/dev/null 2>&1 || { echo "licence files missing"; return 1; }
}

check_chat() {
    command -v eternity-chat >/dev/null || { echo "eternity-chat missing"; return 1; }
    command -v eternity-ai >/dev/null || { echo "eternity-ai missing"; return 1; }
    eternity-ai status 2>&1 | grep -q 'Eternity 08' || { echo "eternity-ai status lacks Eternity 08"; return 1; }
    local out
    out=$(timeout $((300 * SCALE)) eternity-chat --small --ask "Reply with the single word PONG." 2>/dev/null)
    echo "$out" | grep -qi pong || { echo "model did not answer PONG: $(echo "$out" | tail -c 120 | tr '\n' ' ')"; return 1; }
    local bench
    # CSV columns of llama-bench b11843: 7 model_type, 12 n_threads, 35 n_prompt, 36 n_gen, 41 avg_ts
    bench=$(timeout $((300 * SCALE)) llama-bench -m /opt/eternity/models/small.gguf -p 64 -n 32 -o csv 2>/dev/null | tail -n 2 | cut -d, -f 7,12,35,36,41 | tr '\n' ' ')
    echo "INFO bench small (model,threads,n_prompt,n_gen,tok/s): ${bench:-no output}" >&2
    # Also exercise the default (4B) model when the machine has room for it (8 GB class);
    # eternity-chat itself would pick the small one below ETERNITY_MIN_MEM_KB.
    local avail
    avail=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
    if [ "$avail" -ge 5500000 ]; then
        out=$(timeout $((300 * SCALE)) eternity-chat --default --ask "Reply with the single word PONG." 2>/dev/null)
        echo "$out" | grep -qi pong || { echo "default model did not answer PONG: $(echo "$out" | tail -c 120 | tr '\n' ' ')"; return 1; }
        echo "INFO chat: default model answered too" >&2
    else
        echo "INFO chat: default model skipped (MemAvailable ${avail}kB below 5500000kB)" >&2
    fi
}

run_all() {
    local failed=0 name fn reason rc
    for fn in $(declare -F | awk '{print $3}' | grep '^check_' | sort); do
        name=${fn#check_}
        reason=$($fn 2>&1); rc=$?
        case $rc in
            0) echo "CHECK $name: PASS"; [ -n "$reason" ] && echo "$reason" | grep '^INFO' ;;
            2) echo "CHECK $name: SKIP $reason" ;;
            *) echo "CHECK $name: FAIL $reason"; failed=1 ;;
        esac
    done
    return $failed
}

# When sourced by tests/run-chroot-checks.sh only the functions are wanted.
if [ -z "${ETERNITY_SMOKE_SOURCE_ONLY:-}" ]; then
    if run_all; then echo "SMOKE: PASS"; else echo "SMOKE: FAIL"; fi
    echo "SMOKE_DONE"
    sync
    systemctl poweroff
fi

#!/bin/bash
# Eternity 08 build: clean checkout -> ISO.
#
#   ./build.sh            build out/eternity-08-0.1.0-amd64.iso
#   ./build.sh --test     build, then run the QEMU verification suite
#   ./build.sh --clean    purge the live-build caches first
#
# Runs as root inside the Debian 13 WSL2 build host (see tools/wsl-setup.ps1).
# The repo lives on /mnt/c (slow, no POSIX permissions, unsafe for chroots), so the
# tree is mirrored to ETERNITY_BUILD_DIR (default /srv/eternity-build) and built
# there; results are copied back to <repo>/out.
set -euo pipefail

REPO=$(cd "$(dirname "$0")" && pwd)
BUILD_DIR=${ETERNITY_BUILD_DIR:-/srv/eternity-build}
VERSION=0.1.0
ISO_NAME="eternity-08-${VERSION}-amd64.iso"
DO_TEST=0
DO_CLEAN=0
for a in "$@"; do
    case $a in
        --test) DO_TEST=1 ;;
        --clean) DO_CLEAN=1 ;;
        *) echo "unknown option: $a" >&2; exit 2 ;;
    esac
done

[ "$(id -u)" = 0 ] || { echo "build.sh must run as root" >&2; exit 1; }
grep -q '^VERSION_CODENAME=trixie' /etc/os-release || { echo "build host must be Debian 13 (trixie)" >&2; exit 1; }
command -v lb >/dev/null || { echo "live-build not installed (run tools/wsl-setup.ps1)" >&2; exit 1; }

log() { printf '\n==> %s\n' "$*"; }

log "Mirroring $REPO -> $BUILD_DIR"
mkdir -p "$BUILD_DIR"
rsync -a --delete \
    --exclude '.git' --exclude 'cache/' --exclude 'out/' --exclude 'tests/out/' \
    --exclude '.superpowers/' --exclude 'build.log' --exclude '.hostvenv/' \
    --exclude 'config/includes.chroot/opt/eternity/models/*.gguf' \
    --exclude 'config/includes.chroot/opt/eternity/models/*.LICENSE' \
    --exclude 'config/includes.chroot/opt/eternity/models/models.json' \
    --exclude 'config/includes.chroot/opt/eternity/models/SHA256SUMS' \
    --exclude 'config/includes.chroot/var/cache/eternity-wheels/' \
    "$REPO/" "$BUILD_DIR/"
# Big downloaded artifacts stay in the build dir between runs (they are gitignored).
mkdir -p "$BUILD_DIR/config/includes.chroot/opt/eternity/models" "$BUILD_DIR/out"
cd "$BUILD_DIR"

# /mnt/c presents everything as 0777; normalise so the image gets sane modes.
log "Normalising file modes"
find config/includes.chroot config/hooks config/package-lists config/archives config/bootloaders \
     auto tests ai branding -type d -exec chmod 755 {} + 2>/dev/null || true
find config/includes.chroot config/package-lists config/archives config/bootloaders ai branding tests \
     -type f -exec chmod 644 {} + 2>/dev/null || true
chmod 755 build.sh auto/* config/hooks/*/* tests/*.sh 2>/dev/null || true
find config/includes.chroot/usr/lib/eternity config/includes.chroot/usr/local/bin \
     config/includes.chroot/usr/lib/live/config \
     -type f \( -name '*.sh' -o ! -name '*.*' \) -exec chmod 755 {} + 2>/dev/null || true

log "Staging in-image test files"
install -D -m 755 tests/smoke.sh config/includes.chroot/usr/lib/eternity/smoke.sh
if [ -d tests/expect ]; then
    mkdir -p config/includes.chroot/usr/lib/eternity/expect
    cp -a tests/expect/. config/includes.chroot/usr/lib/eternity/expect/
fi
if [ -f ai/requirements.lock ]; then
    install -D -m 644 ai/requirements.lock config/includes.chroot/usr/lib/eternity/requirements.lock
    # Wheel cache for the offline venv build inside the chroot (kept between builds,
    # removed from the image by the cleanup hook). Host and image are both Debian 13 / Python 3.13.
    log "Staging Python wheels"
    WHEELS=config/includes.chroot/var/cache/eternity-wheels
    mkdir -p "$WHEELS"
    [ -x .hostvenv/bin/pip ] || python3 -m venv .hostvenv
    .hostvenv/bin/pip download -q --require-hashes -r ai/requirements.lock -d "$WHEELS"
    # build backends for the sdists in the lock (llama-cpp-python needs scikit-build-core);
    # pip's isolated build env resolves them from the same offline cache inside the chroot.
    .hostvenv/bin/pip download -q 'scikit-build-core>=0.9.2' setuptools wheel -d "$WHEELS"
fi
if [ -f ai/llama-cpp.version ]; then
    install -D -m 644 ai/llama-cpp.version config/includes.chroot/usr/lib/eternity/llama-cpp.version
fi
if [ -f branding/render.py ]; then
    log "Rendering branding assets"
    python3 branding/render.py
fi
if [ -f branding/make-grub-fonts.sh ]; then
    log "Building GRUB fonts"
    bash branding/make-grub-fonts.sh
fi
if [ -f ai/fetch-models.sh ]; then
    log "Fetching models"
    bash ai/fetch-models.sh
fi

if [ "$DO_CLEAN" = 1 ]; then
    log "Purging live-build caches"
    lb clean --purge
fi
log "lb clean"
lb clean
log "lb config"
lb config
# Keep mksquashfs within the WSL memory cap (the 7 GB tree would otherwise peak well above it)
export MKSQUASHFS_OPTIONS="${MKSQUASHFS_OPTIONS:--processors 3 -mem 768M}"
log "lb build (log: $BUILD_DIR/build.log)"
start=$(date +%s)
lb build
end=$(date +%s)

iso=$(ls -1 ./*.iso 2>/dev/null | head -1 || true)
[ -n "$iso" ] && [ -f "$iso" ] || { echo "no ISO produced; see $BUILD_DIR/build.log" >&2; exit 1; }
mv -f "$iso" "out/$ISO_NAME"
[ -f "${iso%.iso}.sha256" ] && mv -f "${iso%.iso}.sha256" "out/$ISO_NAME.sha256" || true
log "ISO: out/$ISO_NAME ($(du -h "out/$ISO_NAME" | cut -f1)), build time $(( (end - start) / 60 )) min"

log "Copying results back to $REPO/out"
mkdir -p "$REPO/out"
cp -f "out/$ISO_NAME" "$REPO/out/"
cp -f build.log "$REPO/out/build.log"
[ -f "out/$ISO_NAME.sha256" ] && cp -f "out/$ISO_NAME.sha256" "$REPO/out/" || true

if [ "$DO_TEST" = 1 ]; then
    if [ -f tests/run-all.sh ]; then
        log "Running the verification suite"
        bash tests/run-all.sh "out/$ISO_NAME"
    else
        log "Running the QEMU smoke test"
        bash tests/run-qemu-smoke.sh "out/$ISO_NAME"
    fi
    rc=$?
    mkdir -p "$REPO/tests/out"
    cp -af tests/out/. "$REPO/tests/out/" 2>/dev/null || true
    exit $rc
fi

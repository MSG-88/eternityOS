# Eternity 08 build host: a Debian 13 (trixie) WSL2 instance named "Debian".
# Run from an elevated PowerShell. Idempotent.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Packages = @(
  'live-build','debootstrap','squashfs-tools','xorriso','mtools','dosfstools',
  'qemu-system-x86','ovmf','python3','python3-pip','python3-venv','python3-cairosvg',
  'python3-pil','git','curl','ca-certificates','librsvg2-bin','fonts-inter',
  'fonts-jetbrains-mono','rsync','file','grub-common','grub-efi-amd64-bin','grub-pc-bin',
  'isolinux','syslinux-common','cpio','zstd','xz-utils','mokutil'
) -join ' '

function Get-WslDistros {
  # wsl.exe prints UTF-16; normalise and strip NULs.
  $raw = & wsl.exe -l -q 2>$null
  if ($null -eq $raw) { return @() }
  return @($raw | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ -ne '' })
}

function Invoke-Debian([string]$Cmd) {
  & wsl.exe -d Debian -u root -- bash -lc $Cmd
  if ($LASTEXITCODE -ne 0) { throw "command failed in Debian WSL: $Cmd" }
}

function Get-DebianCodename {
  # grep form: a "$VAR" inside the command does not survive wsl.exe's argument passing reliably.
  $out = & wsl.exe -d Debian -u root -- bash -lc 'grep ^VERSION_CODENAME= /etc/os-release | cut -d= -f2' 2>$null
  if ($null -eq $out) { return '' }
  return (($out | Out-String) -replace "`0", '').Trim()
}

if ((Get-WslDistros) -notcontains 'Debian') {
  Write-Host 'Installing Debian WSL distribution...'
  & wsl.exe --install -d Debian --no-launch
  if ($LASTEXITCODE -ne 0) { throw 'wsl --install -d Debian failed' }
}

# The distro can take a moment to become launchable after --install.
$codename = ''
for ($i = 0; $i -lt 6 -and $codename -eq ''; $i++) {
  $codename = Get-DebianCodename
  if ($codename -eq '') { Start-Sleep -Seconds 10 }
}
Write-Host "Debian codename: '$codename'"
if ($codename -ne 'trixie') {
  Write-Host 'Installed Debian is not trixie; replacing it with a Debian 13 rootfs (debuerreotype, the source of the official Docker images).'
  & wsl.exe --unregister Debian | Out-Null
  $dl = Join-Path $env:TEMP 'eternity-debian-wsl'
  New-Item -ItemType Directory -Force $dl | Out-Null
  $tar = Join-Path $dl 'trixie-rootfs.tar.xz'
  Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/debuerreotype/docker-debian-artifacts/raw/dist-amd64/trixie/rootfs.tar.xz' -OutFile $tar
  $vhdDir = Join-Path $env:LOCALAPPDATA 'WSL\Debian'
  New-Item -ItemType Directory -Force $vhdDir | Out-Null
  & wsl.exe --import Debian $vhdDir $tar --version 2
  if ($LASTEXITCODE -ne 0) { throw 'wsl --import failed' }
  $codename = Get-DebianCodename
  if ($codename -ne 'trixie') { throw "still not trixie after reinstall: '$codename'" }
}

Write-Host 'Configuring /etc/wsl.conf (root default user, systemd) ...'
Invoke-Debian "printf '[user]\ndefault=root\n[boot]\nsystemd=true\n' > /etc/wsl.conf"

Write-Host 'Updating packages and installing the build toolchain ...'
Invoke-Debian "export DEBIAN_FRONTEND=noninteractive; apt-get update -q && apt-get -y -q full-upgrade && apt-get -y -q install $Packages && apt-get clean"

& wsl.exe --terminate Debian | Out-Null
Write-Host 'Done. Verify with:'
Write-Host "  wsl -d Debian -u root -- bash -lc 'grep VERSION_CODENAME /etc/os-release; lb --version'"

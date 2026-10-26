<#
.SYNOPSIS
  Write the Eternity 08 ISO to a USB stick as a raw image (the correct way for a Debian live
  hybrid ISO), from Windows. This is the DD-mode equivalent: it copies the ISO byte-for-byte to
  the whole disk, preserving the El Torito / isohybrid / Secure Boot layout.

.WHY
  Rufus in "ISO" (partition) mode extracts the ISO onto a new FAT partition and rebuilds the
  bootloader; on a Debian hybrid ISO that breaks the boot chain and the firmware drops to a
  "grub>" prompt. Writing the image raw (this script, Rufus "DD" mode, or balenaEtcher) keeps the
  layout intact so it boots under UEFI + Secure Boot.

.USAGE
  List removable disks:   powershell -ExecutionPolicy Bypass -File write-eternity-usb.ps1 -List
  Write to disk 2:        powershell -ExecutionPolicy Bypass -File write-eternity-usb.ps1 -DiskNumber 2
  (run from an elevated PowerShell; the ISO defaults to ..\..\out\eternity-08-0.1.0-amd64.iso)

.WARNING
  This ERASES the target disk completely. Pick the USB stick's disk number carefully (-List shows
  model, size and bus type). The script refuses system/boot disks and anything not on the USB bus.
#>
[CmdletBinding()]
param(
    [string]$IsoPath = (Join-Path $PSScriptRoot '..\..\out\eternity-08-0.1.0-amd64.iso'),
    [int]$DiskNumber = -1,
    [switch]$List,
    [switch]$Yes
)
$ErrorActionPreference = 'Stop'

function Show-UsbDisks {
    Get-Disk | Where-Object { $_.BusType -eq 'USB' } |
        Select-Object Number, FriendlyName,
            @{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}}, BusType, PartitionStyle, OperationalStatus |
        Format-Table -AutoSize
}

if ($List -or $DiskNumber -lt 0) {
    "Removable (USB) disks:`n"
    Show-UsbDisks
    if ($DiskNumber -lt 0) { "`nRe-run with -DiskNumber <N> to write. Use -List any time to see this."; return }
}

# --- checks -----------------------------------------------------------------------------------
if (-not (Test-Path $IsoPath)) { throw "ISO not found: $IsoPath" }
$IsoPath = (Resolve-Path $IsoPath).Path
$isoSize = (Get-Item $IsoPath).Length

$disk = Get-Disk -Number $DiskNumber -ErrorAction Stop
if ($disk.BusType -ne 'USB') { throw "Disk $DiskNumber is a $($disk.BusType) disk ('$($disk.FriendlyName)'), not USB. Refusing (use -List)." }
if ($disk.IsSystem -or $disk.IsBoot)  { throw "Disk $DiskNumber is a system/boot disk. Refusing." }
if ($disk.Size -lt $isoSize) { throw "Disk $DiskNumber ($([math]::Round($disk.Size/1GB,1)) GB) is smaller than the ISO ($([math]::Round($isoSize/1GB,2)) GB)." }

"About to ERASE and write:"
"  ISO : $IsoPath ($([math]::Round($isoSize/1GB,2)) GB)"
"  Disk: $DiskNumber  $($disk.FriendlyName)  $([math]::Round($disk.Size/1GB,1)) GB  ($($disk.BusType))"
if (-not $Yes) {
    $ans = Read-Host "Type the disk number again to confirm ERASE"
    if ($ans -ne "$DiskNumber") { "Aborted."; return }
}

# --- write ------------------------------------------------------------------------------------
"Clearing partitions on disk $DiskNumber ..."
Clear-Disk -Number $DiskNumber -RemoveData -RemoveOEM -Confirm:$false -ErrorAction SilentlyContinue
Set-Disk -Number $DiskNumber -IsOffline $true -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$src = [System.IO.File]::Open($IsoPath, 'Open', 'Read', 'Read')
$dst = $null
try {
    $path = "\\.\PhysicalDrive$DiskNumber"
    $dst = [System.IO.File]::Open($path, 'Open', 'ReadWrite', 'None')
    $buf = New-Object byte[] (8MB)
    $written = 0L; $sw = [System.Diagnostics.Stopwatch]::StartNew(); $lastPct = -1
    while (($n = $src.Read($buf, 0, $buf.Length)) -gt 0) {
        $dst.Write($buf, 0, $n); $written += $n
        $pct = [int](($written * 100) / $isoSize)
        if ($pct -ne $lastPct) {
            $mbps = if ($sw.Elapsed.TotalSeconds -gt 0) { [math]::Round(($written/1MB)/$sw.Elapsed.TotalSeconds,1) } else { 0 }
            Write-Progress -Activity "Writing Eternity 08 to disk $DiskNumber" -Status "$pct% ($([math]::Round($written/1MB)) MB, $mbps MB/s)" -PercentComplete $pct
            $lastPct = $pct
        }
    }
    $dst.Flush()
    Write-Progress -Activity "Writing" -Completed
    "Wrote $([math]::Round($written/1MB)) MB in $([math]::Round($sw.Elapsed.TotalSeconds)) s."
}
finally {
    if ($dst) { $dst.Close() }
    $src.Close()
    Set-Disk -Number $DiskNumber -IsOffline $false -ErrorAction SilentlyContinue
}
"Done. Safely eject, then boot it from the one-time boot menu (Esc/F8 at power-on)."
"On the ASUS ROG: if the screen stays black after GRUB, pick 'Eternity 08 Live (safe graphics)',"
"or set the GPU to Eco (iGPU) in Armoury Crate for the first boot (see docs/hardware/asus-g635lw.md)."

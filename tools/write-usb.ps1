# Write the Eternity 08 ISO to a USB stick (raw/dd mode). Run from an elevated PowerShell.
#
#   .\write-usb.ps1 -List
#   .\write-usb.ps1 -DiskNumber 2 -Iso out\eternity-08-0.1.0-amd64.iso -Confirm:$true
#
# Safety: only disks with BusType USB are accepted, never the system disk, and the
# write requires confirmation (ConfirmImpact=High prompts; -Confirm:$true keeps the
# prompt explicit, -Confirm:$false would skip it). Everything on the stick is destroyed.
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param(
  [switch]$List,
  [int]$DiskNumber = -1,
  [string]$Iso
)
$ErrorActionPreference = 'Stop'

function Get-UsbDisks { Get-Disk | Where-Object { $_.BusType -eq 'USB' } }

if ($List -or $DiskNumber -lt 0) {
  $usb = @(Get-UsbDisks)
  if ($usb.Count -eq 0) { Write-Host 'no removable USB disks found'; return }
  $usb | Select-Object Number, FriendlyName, @{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}}, BusType, IsSystem, IsBoot | Format-Table -AutoSize
  return
}

if (-not $Iso) { throw 'specify -Iso <path>' }
if (-not (Test-Path $Iso)) { throw "ISO not found: $Iso" }
$disk = Get-Disk -Number $DiskNumber -ErrorAction Stop
if ($disk.BusType -ne 'USB') { throw "refusing: disk $DiskNumber ($($disk.FriendlyName)) is not a USB disk (BusType=$($disk.BusType))" }
if ($disk.IsSystem -or $disk.IsBoot) { throw "refusing: disk $DiskNumber is the system/boot disk" }
$sysDisk = (Get-Partition -DriveLetter ($env:SystemDrive.TrimEnd(':'))).DiskNumber
if ($disk.Number -eq $sysDisk) { throw "refusing: disk $DiskNumber hosts $env:SystemDrive" }

$isoFull = (Resolve-Path $Iso).Path
$size = (Get-Item $isoFull).Length
if ($size -gt $disk.Size) { throw "ISO ($([math]::Round($size/1GB,2)) GB) is larger than the disk ($([math]::Round($disk.Size/1GB,2)) GB)" }
Write-Host ("Target: disk {0}  {1}  {2:N1} GB  (USB)" -f $disk.Number, $disk.FriendlyName, ($disk.Size/1GB))
Write-Host ("Image : {0}  {1:N2} GB" -f $isoFull, ($size/1GB))

if (-not $PSCmdlet.ShouldProcess("disk $($disk.Number) ($($disk.FriendlyName))", "ERASE and write $isoFull")) { return }

Write-Host 'Clearing the disk ...'
if ($disk.PartitionStyle -ne 'RAW') { Clear-Disk -Number $disk.Number -RemoveData -RemoveOEM -Confirm:$false }
# Fixed disks are taken offline so Windows leaves them alone during the raw write. Removable
# media cannot be set offline ("Not Supported"); after Clear-Disk they have no volumes left
# that could interfere, so the write proceeds without it.
try { Set-Disk -Number $disk.Number -IsOffline $true -ErrorAction Stop } catch { Write-Host "  (cannot take the disk offline: $($_.Exception.Message.Trim()); continuing)" }
try { Set-Disk -Number $disk.Number -IsReadOnly $false -ErrorAction Stop } catch {}

$dev = "\\.\PhysicalDrive$($disk.Number)"
$buf = New-Object byte[] (4MB)
$in = [System.IO.File]::OpenRead($isoFull)
$out = New-Object System.IO.FileStream($dev, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None, 4MB, [System.IO.FileOptions]::WriteThrough)
# Windows re-reads the partition table as soon as it lands on the stick and mounts the new
# volumes, which broke a raw write half way ("The device is not ready" after 4 GB on
# 2026-10-25). So the first megabyte (protective MBR + GPT header) is written last: until
# then the stick looks blank to Windows and nothing grabs it.
$HEAD = 1MB
try {
  $t0 = Get-Date; $done = $HEAD; $reported = $HEAD
  $in.Position = $HEAD; $out.Position = $HEAD
  while (($n = $in.Read($buf, 0, $buf.Length)) -gt 0) {
    if ($n % 512 -ne 0) { $pad = 512 - ($n % 512); [Array]::Clear($buf, $n, $pad); $n += $pad }
    $out.Write($buf, 0, $n); $done += $n
    if (($done - $reported) -ge 256MB) { $reported = $done; Write-Host ("  {0:N0} MB written ({1:N1} MB/s)" -f ($done/1MB), (($done-$HEAD)/1MB/((Get-Date)-$t0).TotalSeconds)) }
  }
  $out.Flush()
  $in.Position = 0; $out.Position = 0
  $n = $in.Read($buf, 0, $HEAD); $out.Write($buf, 0, $n); $out.Flush()
  Write-Host ("  {0:N0} MB written, partition table in place" -f ($done/1MB))
} finally { $out.Dispose(); $in.Dispose() }


Write-Host 'Verifying the first 64 MB ...'
$verify = [Math]::Min(64MB, $size)
$sha = [System.Security.Cryptography.SHA256]::Create()
$a = [System.IO.File]::OpenRead($isoFull); $ba = New-Object byte[] $verify; [void]$a.Read($ba, 0, $verify); $a.Dispose()
$r = New-Object System.IO.FileStream($dev, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None, 4MB); $bb = New-Object byte[] $verify; [void]$r.Read($bb, 0, $verify); $r.Dispose()
$ha = [BitConverter]::ToString($sha.ComputeHash($ba)); $hb = [BitConverter]::ToString($sha.ComputeHash($bb))
Set-Disk -Number $disk.Number -IsOffline $false -ErrorAction SilentlyContinue
if ($ha -ne $hb) { throw 'verification FAILED: data read back differs from the ISO' }
Write-Host 'Done. The stick is ready: boot the laptop from it (MSI: F11 boot menu), Secure Boot can stay on.'

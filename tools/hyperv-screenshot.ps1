# Capture the console of a Hyper-V VM to a PNG (dot-source or run directly).
#   .\hyperv-screenshot.ps1 -VMName Eternity08-Test -Path shot.png [-Width 1280 -Height 720]
param(
  [Parameter(Mandatory=$true)][string]$VMName,
  [Parameter(Mandatory=$true)][string]$Path,
  [int]$Width = 1280,
  [int]$Height = 720
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

function Get-VMScreenshot([string]$Name, [string]$OutPath, [int]$W, [int]$H) {
  $ns = 'root\virtualization\v2'
  $vmms = Get-WmiObject -Namespace $ns -Class Msvm_VirtualSystemManagementService
  $vm = Get-WmiObject -Namespace $ns -Class Msvm_ComputerSystem -Filter "ElementName='$Name'"
  if ($null -eq $vm) { throw "VM not found: $Name" }
  $settings = $vm.GetRelated('Msvm_VirtualSystemSettingData') | Where-Object { $_.VirtualSystemType -eq 'Microsoft:Hyper-V:System:Realized' }
  $img = $vmms.GetVirtualSystemThumbnailImage($settings, $W, $H).ImageData
  if ($null -eq $img -or $img.Length -eq 0) { throw "no image data (is the VM running?)" }
  $bmp = New-Object System.Drawing.Bitmap -ArgumentList $W, $H, ([System.Drawing.Imaging.PixelFormat]::Format16bppRgb565)
  $rect = New-Object System.Drawing.Rectangle 0, 0, $W, $H
  $data = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::WriteOnly, [System.Drawing.Imaging.PixelFormat]::Format16bppRgb565)
  [System.Runtime.InteropServices.Marshal]::Copy($img, 0, $data.Scan0, [Math]::Min($img.Length, $data.Stride * $data.Height))
  $bmp.UnlockBits($data)
  $full = [System.IO.Path]::GetFullPath($OutPath)
  $bmp.Save($full, [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  return $full
}

Get-VMScreenshot -Name $VMName -OutPath $Path -W $Width -H $Height

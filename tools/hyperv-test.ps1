# Hyper-V test driver for the Eternity 08 ISO (run from an elevated PowerShell).
#
#   .\hyperv-test.ps1 -Iso out\eternity-08-0.1.0-amd64.iso -Scenario live
#       creates/recreates the VM (Gen 2, Secure Boot with the Microsoft UEFI CA template),
#       boots the ISO, screenshots GRUB/splash/login, logs in, opens a terminal, runs
#       eternity-ai status and a one-shot eternity-chat, screenshotting each step into
#       docs\screenshots\hyperv-*.png
#
#   There is no scripted -Install scenario: the Calamares run is driven step by step with
#   the single actions below (screenshot, type, key), then -Action boot-disk and start.
#   Single actions (for driving the installer by hand):
#   .\hyperv-test.ps1 -Action create -Iso <iso> | start | shot -Name <file> | type -Text "..." |
#                     key -Key Enter|Tab|Down|CtrlAltT | stop | boot-disk | destroy
param(
  [string]$Iso,
  [ValidateSet('live','')][string]$Scenario = '',
  [ValidateSet('create','start','shot','type','key','stop','boot-disk','destroy','')][string]$Action = '',
  [string]$Name = 'shot',
  [string]$Text = '',
  [string]$Key = '',
  [string]$VMName = 'Eternity08-Test',
  [int]$MemoryGB = 8,
  [int]$Cpus = 4
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Shots = Join-Path $Root 'docs\screenshots'
$Vhd = Join-Path $Root "out\$VMName.vhdx"
New-Item -ItemType Directory -Force $Shots | Out-Null

function Shot([string]$n) {
  $p = Join-Path $Shots "hyperv-$n.png"
  & (Join-Path $Root 'tools\hyperv-screenshot.ps1') -VMName $VMName -Path $p | Out-Null
  Write-Host "screenshot: $p"
}
function Kbd() {
  $vm = Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'"
  return $vm.GetRelated('Msvm_Keyboard')
}
function TypeText([string]$t) { (Kbd).TypeText($t) | Out-Null; Start-Sleep -Milliseconds 300 }
function PressKey([string]$k) {
  $kb = Kbd
  $codes = @{ Enter=0x0D; Tab=0x09; Down=0x28; Up=0x26; Esc=0x1B; Space=0x20; Left=0x25; Right=0x27; F10=0x79 }
  switch ($k) {
    'CtrlAltT' { $kb.PressKey(0x11) | Out-Null; $kb.PressKey(0x12) | Out-Null; $kb.TypeKey(0x54) | Out-Null; $kb.ReleaseKey(0x12) | Out-Null; $kb.ReleaseKey(0x11) | Out-Null }
    default { if (-not $codes.ContainsKey($k)) { throw "unknown key $k" }; $kb.TypeKey($codes[$k]) | Out-Null }
  }
  Start-Sleep -Milliseconds 300
}
function Create([string]$isoPath) {
  if (-not (Test-Path $isoPath)) { throw "ISO not found: $isoPath" }
  $isoFull = (Resolve-Path $isoPath).Path
  if (Get-VM -Name $VMName -ErrorAction SilentlyContinue) { Destroy }
  New-Item -ItemType Directory -Force (Split-Path $Vhd) | Out-Null
  if (Test-Path $Vhd) { Remove-Item -Force $Vhd }
  New-VM -Name $VMName -Generation 2 -MemoryStartupBytes ($MemoryGB * 1GB) -NewVHDPath $Vhd -NewVHDSizeBytes 40GB -SwitchName 'Default Switch' | Out-Null
  Set-VM -Name $VMName -ProcessorCount $Cpus -StaticMemory -AutomaticCheckpointsEnabled $false -CheckpointType Disabled
  Set-VMFirmware -VMName $VMName -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
  Add-VMDvdDrive -VMName $VMName -Path $isoFull
  $dvd = Get-VMDvdDrive -VMName $VMName
  Set-VMFirmware -VMName $VMName -FirstBootDevice $dvd
  Write-Host "VM $VMName created: Gen2, Secure Boot (Microsoft UEFI CA), $MemoryGB GB, $Cpus vCPU, DVD first"
}
function Destroy() {
  $vm = Get-VM -Name $VMName -ErrorAction SilentlyContinue
  if ($vm) {
    if ($vm.State -ne 'Off') { Stop-VM -Name $VMName -TurnOff -Force }
    Remove-VM -Name $VMName -Force
  }
  if (Test-Path $Vhd) { Remove-Item -Force $Vhd }
  Write-Host "VM $VMName removed"
}
function BootDisk() {
  $hdd = Get-VMHardDiskDrive -VMName $VMName
  Set-VMFirmware -VMName $VMName -FirstBootDevice $hdd
  Get-VMDvdDrive -VMName $VMName | Remove-VMDvdDrive
  Write-Host "boot order: disk first, DVD removed"
}

switch ($Action) {
  'create'    { Create $Iso; return }
  'start'     { Start-VM -Name $VMName; Write-Host 'started'; return }
  'shot'      { Shot $Name; return }
  'type'      { TypeText $Text; return }
  'key'       { PressKey $Key; return }
  'stop'      { Stop-VM -Name $VMName -TurnOff -Force; Write-Host 'stopped'; return }
  'boot-disk' { BootDisk; return }
  'destroy'   { Destroy; return }
}

if ($Scenario -eq 'live') {
  Create $Iso
  Start-VM -Name $VMName
  $t0 = Get-Date
  Start-Sleep -Seconds 10; Shot 'grub'
  PressKey 'Enter'
  Start-Sleep -Seconds 8;  Shot 'splash'
  Start-Sleep -Seconds 40; Shot 'login'
  $tLogin = ((Get-Date) - $t0).TotalSeconds
  TypeText 'eternity'; PressKey 'Enter'   # the greeter preselects the live user; this is the password
  Start-Sleep -Seconds 30; Shot 'desktop'
  PressKey 'CtrlAltT'; Start-Sleep -Seconds 8
  TypeText 'free -m; eternity-ai status'; PressKey 'Enter'; Start-Sleep -Seconds 12; Shot 'status'
  TypeText 'eternity-chat --small --ask "Say hello in five words."'; PressKey 'Enter'
  Start-Sleep -Seconds 120; Shot 'chat'
  Write-Host ("login screen reached at ~{0:N0} s after power-on (screenshot time)" -f $tLogin)
  Write-Host 'live scenario done; VM left running for inspection (use -Action stop / destroy)'
}

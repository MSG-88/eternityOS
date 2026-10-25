# Eternity session: press Super+V (push-to-talk) and capture what the ask bar says.
param([string]$Prefix = 'vt')
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 90 }
function Combo([int]$mod, [int]$code) { $k = Kbd; $k.PressKey($mod) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($mod) | Out-Null; Start-Sleep -Milliseconds 300 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
$LWIN = 0x5B; $ESC = 0x1B
Key $ESC; Start-Sleep 1
Combo $LWIN 0x56; Start-Sleep 2; Shot "$Prefix-2s"
Start-Sleep 7; Shot "$Prefix-9s"
Key $ESC
"done $(Get-Date -Format HH:mm:ss)"

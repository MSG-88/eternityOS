# A consent card is up: Enter allows it; capture the answer that follows.
param([string]$Prefix = 'cc')
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
(Kbd).TypeKey(0x0D) | Out-Null
Start-Sleep 3; Shot "$Prefix-allowed"
Start-Sleep 20; Shot "$Prefix-25s"
Start-Sleep 30; Shot "$Prefix-55s"
Start-Sleep 30; Shot "$Prefix-85s"
"done $(Get-Date -Format HH:mm:ss)"

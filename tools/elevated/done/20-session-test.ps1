# Restart the Hyper-V test VM into the "Eternity shell" GRUB entry (4th), log in at the greeter and
# screenshot the session as it comes up: tests\out\hyperv\e-*.png. Keyboard goes through the WMI
# Msvm_Keyboard (virtual-key codes), which types reliably at native speed.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
New-Item -ItemType Directory -Force $Shots | Out-Null
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 250 }
function Text([string]$t) { (Kbd).TypeText($t) | Out-Null; Start-Sleep -Milliseconds 300 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function At([int]$sec) { $w = $sec - [int]((Get-Date) - $script:t0).TotalSeconds; if ($w -gt 0) { Start-Sleep -Seconds $w } }

$vm = Get-VM -Name $VMName
if ($vm.State -ne 'Off') { Stop-VM -Name $VMName -TurnOff -Force; Start-Sleep -Seconds 2 }
Start-VM -Name $VMName
$script:t0 = Get-Date
"started $t0"
At 7;  Shot 'e-grub0'
Key 0x28; Key 0x28; Key 0x28          # Down x3 -> "Eternity 08 Live (Eternity shell)"
Shot 'e-grub'; Key 0x0D               # Enter
At 16; Shot 'e-splash'
At 30; Shot 'e-splash2'
At 55; Shot 'e-login'
Text 'eternity'; Key 0x0D             # greeter password
At 75; Shot 'e-session-20s'
At 100; Shot 'e-session-45s'
At 130; Shot 'e-session-75s'
"done $(Get-Date -Format HH:mm:ss)"

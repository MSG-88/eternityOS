# Eternity session: pull the current repo files into the running system with one short line
# (tools/dev/e8pull.sh served from the repo root), then screenshot the restarted shell.
param([string]$Password = 'eternity2026!', [string]$HostIp = '172.24.208.1', [string]$Prefix = 'pu')
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 90 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 50; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 50; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 90 }
function Combo([int]$mod, [int]$code) { $k = Kbd; $k.PressKey($mod) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($mod) | Out-Null; Start-Sleep -Milliseconds 300 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } '|' { Shifted 0xDC } '!' { Shifted 0x31 } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
Key $ESC; Start-Sleep 1; Key $ESC; Start-Sleep 1
Combo $LWIN $RET; Start-Sleep 7; Shot "$Prefix-terminal"
$k = Kbd; $k.PressKey(0x11) | Out-Null; $k.TypeKey(0x43) | Out-Null; $k.ReleaseKey(0x11) | Out-Null; Start-Sleep 1
TypeStr 'sudo -v'; Key $RET; Start-Sleep 4; TypeStr $Password; Key $RET; Start-Sleep 3
TypeStr "curl -fsS http://${HostIp}:8790/tools/dev/e8pull.sh | sudo bash -s $HostIp"; Key $RET
Start-Sleep 25; Shot "$Prefix-pulled"
TypeStr 'exit'; Key $RET; Start-Sleep 8; Shot "$Prefix-shell"
"done $(Get-Date -Format HH:mm:ss)"

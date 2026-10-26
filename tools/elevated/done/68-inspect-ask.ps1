# Close the Monitor and Settings windows, look at the processes and the daemon log, then show the
# ask bar again to see the answer or its status. Shots: tests\out\hyperv\i-*.png
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 110 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 60; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 60; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 110 }
function Combo([int]$mod, [int]$code) { $k = Kbd; $k.PressKey($mod) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($mod) | Out-Null; Start-Sleep -Milliseconds 300 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '|' { Shifted 0xDC } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
Combo $LWIN $RET; Start-Sleep 7
TypeStr 'hyprctl dispatch closewindow class:eternity-monitor; hyprctl dispatch closewindow class:eternity-settings; top -bn1 | head -n 14; tail -n 10 /home/eternity/.local/state/eternity/ui.log'; Key $RET
Start-Sleep 6; Shot 'i-terminal'
TypeStr 'exit'; Key $RET; Start-Sleep 3
Combo $LWIN 0x20; Start-Sleep 3; Shot 'i-ask'
Key $ESC
"done $(Get-Date -Format HH:mm:ss)"

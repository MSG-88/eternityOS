# In the open terminal of the Eternity session: the daemon's traceback for the Claude ask.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 100 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 60; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 60; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 100 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '?' { Shifted 0xBF } '|' { Shifted 0xDC } '~' { Shifted 0xC0 } "'" { Key 0xDE } '>' { Shifted 0xBE } '<' { Shifted 0xBC } '=' { Key 0xBB } '(' { Shifted 0x39 } ')' { Shifted 0x30 } '"' { Shifted 0xDE } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$k = Kbd; $k.PressKey(0x11) | Out-Null; $k.TypeKey(0x43) | Out-Null; $k.ReleaseKey(0x11) | Out-Null; Start-Sleep 1
TypeStr "clear; journalctl --user -b --no-pager | grep -iE 'Traceback|IndexError|File .*eternity' -A3 | tail -n 40 | cut -c1-170"; Key 0x0D
Start-Sleep 6; Shot 'j-traceback'
TypeStr "clear; cat ~/.local/state/eternity/last-metrics.json; echo; tail -n 5 ~/.local/state/eternity/actions.log | cut -c1-170; systemctl --user status eternity-daemon --no-pager 2>/dev/null | head -n 5; ps -o pid,comm,args -C eternity-daemon,python3 | cut -c1-120"; Key 0x0D
Start-Sleep 6; Shot 'j-metrics'
"done $(Get-Date -Format HH:mm:ss)"

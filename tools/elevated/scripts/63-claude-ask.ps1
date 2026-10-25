# After the owner finished the OAuth sign-in in the VM: ask Claude through Eternity, screenshot
# the answer, list sessions, check the Monitor and the hook audit. Shots: tests\out\hyperv\ca-*.png
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '?' { Shifted 0xBF } '|' { Shifted 0xDC } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
# the sign-in terminal may still be open: close it first
$k = Kbd; $k.PressKey(0x11) | Out-Null; $k.TypeKey(0x43) | Out-Null; $k.ReleaseKey(0x11) | Out-Null; Start-Sleep 1
TypeStr 'clear; claude auth status'; Key $RET; Start-Sleep 5; Shot 'ca-authstatus'
TypeStr 'exit'; Key $RET; Start-Sleep 2
Combo $LWIN 0x20; Start-Sleep 2; TypeStr 'Which window manager am I running and what is its version?'; Shot 'ca-typed'; Key $RET
Start-Sleep 30; Shot 'ca-answer-30s'
Start-Sleep 30; Shot 'ca-answer-60s'
Start-Sleep 30; Shot 'ca-answer-90s'
TypeStr '/sessions'; Key $RET; Start-Sleep 4; Shot 'ca-sessions'
Key $ESC; Start-Sleep 2
Combo $LWIN 0x4D; Start-Sleep 4; Shot 'ca-monitor'; Key $ESC; Start-Sleep 2
Combo $LWIN $RET; Start-Sleep 6
TypeStr 'journalctl --user -b --no-pager 2>/dev/null | grep -i claude-hook | tail -n 12; tail -n 8 /home/eternity/.local/state/eternity/ui.log'; Key $RET
Start-Sleep 5; Shot 'ca-audit'
"done $(Get-Date -Format HH:mm:ss)"

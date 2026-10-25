# Installed system, Eternity session, Claude signed in: ask through the ask bar, capture the
# streamed answer, the session list, the Monitor and the audit log. Shots: tests\out\hyperv\ce-*.png
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '?' { Shifted 0xBF } '|' { Shifted 0xDC } '~' { Shifted 0xC0 } "'" { Key 0xDE } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
Combo $LWIN 0x20; Start-Sleep 2; Shot 'ce-ask-open'
TypeStr 'Which window manager am I running, what is its version, and how many CPU cores does this machine have?'; Shot 'ce-typed'; Key $RET
Start-Sleep 12; Shot 'ce-12s'
Start-Sleep 18; Shot 'ce-30s'
Start-Sleep 30; Shot 'ce-60s'
Start-Sleep 30; Shot 'ce-90s'
TypeStr '/sessions'; Key $RET; Start-Sleep 4; Shot 'ce-sessions'
Key $ESC; Start-Sleep 2
Combo $LWIN 0x4D; Start-Sleep 5; Shot 'ce-monitor'                                 # Super+M
Combo $LWIN $RET; Start-Sleep 7
TypeStr 'journalctl --user -b --no-pager 2>/dev/null | grep -i claude-hook | tail -n 10; tail -n 6 ~/.local/state/eternity/ui.log; ls ~/.local/state/eternity/'; Key $RET
Start-Sleep 6; Shot 'ce-audit'
"done $(Get-Date -Format HH:mm:ss)"

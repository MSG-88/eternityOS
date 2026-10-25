# On the running build 14 session: ask the on-device model through the ask bar and screenshot the
# answer, then the Monitor and the Settings > Assistant page (where Claude sign-in lives).
# Shots: tests\out\hyperv\llm-*.png
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '?' { Shifted 0xBF } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
Combo $LWIN 0x20; Start-Sleep 2; Shot 'llm-ask-open'                       # Super+Space
TypeStr 'What hardware is this machine and how much memory does it have?'; Shot 'llm-ask-typed'; Key $RET
Start-Sleep 25; Shot 'llm-answer-25s'
Start-Sleep 35; Shot 'llm-answer-60s'
Start-Sleep 30; Shot 'llm-answer-90s'
Key $ESC; Start-Sleep 2
Combo $LWIN 0x4D; Start-Sleep 4; Shot 'llm-monitor'; Key $ESC; Start-Sleep 2    # Super+M
Combo $LWIN 0xBC; Start-Sleep 4; Shot 'llm-settings'                           # Super+, : Settings (Assistant page has the Claude sign-in)
"done $(Get-Date -Format HH:mm:ss)"

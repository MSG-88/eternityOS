# Eternity session: open a terminal (Super+Return), run one command, screenshot the output, close it.
param([string]$Command = 'cat ~/.config/eternity/settings.json', [string]$Prefix = 'tc', [int]$Wait = 4)
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '?' { Shifted 0xBF } "'" { Key 0xDE } '"' { Shifted 0xDE } '|' { Shifted 0xDC } '~' { Shifted 0xC0 } '$' { Shifted 0x34 } '=' { Key 0xBB } '!' { Shifted 0x31 } '*' { Shifted 0x38 } '(' { Shifted 0x39 } ')' { Shifted 0x30 } '[' { Key 0xDB } ']' { Key 0xDD } '{' { Shifted 0xDB } '}' { Shifted 0xDD } '&' { Shifted 0x37 } '>' { Shifted 0xBE } '<' { Shifted 0xBC } '\' { Key 0xDC } '+' { Shifted 0xBB } '@' { Shifted 0x32 } '#' { Shifted 0x33 } '%' { Shifted 0x35 } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } elseif ([char]::IsDigit($ch)) { Key ([int][char]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
Key $ESC; Start-Sleep 1; Key $ESC; Start-Sleep 1
Combo $LWIN $RET; Start-Sleep 6
TypeStr $Command; Key $RET
Start-Sleep $Wait; Shot "$Prefix-out"
TypeStr 'exit'; Key $RET; Start-Sleep 2
"done $(Get-Date -Format HH:mm:ss)"

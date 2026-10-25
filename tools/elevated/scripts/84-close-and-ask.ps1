# Eternity session: close every open window (Super+Q, up to 4 times), then ask Claude one question and
# capture the presence sliding left with the answer in the right column.
param([string]$Question = 'Which window manager am I running, what is its version, and how many CPU cores does this machine have?', [string]$Prefix = 'ra')
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '?' { Shifted 0xBF } "'" { Key 0xDE } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
Key $ESC; Start-Sleep 1; Key $ESC; Start-Sleep 1
for ($i = 0; $i -lt 4; $i++) { Combo $LWIN 0x51; Start-Sleep 1 }
Start-Sleep 2; Shot "$Prefix-empty"
Combo $LWIN 0x20; Start-Sleep 2
TypeStr $Question; Shot "$Prefix-typed"; Key $RET
Start-Sleep 12; Shot "$Prefix-12s"
Start-Sleep 25; Shot "$Prefix-37s"
Start-Sleep 30; Shot "$Prefix-67s"
Start-Sleep 30; Shot "$Prefix-97s"
"done $(Get-Date -Format HH:mm:ss)"

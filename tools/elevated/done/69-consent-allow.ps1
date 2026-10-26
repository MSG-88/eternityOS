# Live-patch Consent.qml (Enter = allow) from the VT, restart the shell (the daemon replays the
# pending consent), allow it with Enter and capture the on-device answer. Shots: tests\out\hyperv\k-*.png
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 110 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 60; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 60; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 110 }
function Combo2([int]$m1, [int]$m2, [int]$code) { $k = Kbd; $k.PressKey($m1) | Out-Null; $k.PressKey($m2) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($m2) | Out-Null; $k.ReleaseKey($m1) | Out-Null; Start-Sleep -Milliseconds 400 }
function Combo([int]$mod, [int]$code) { $k = Kbd; $k.PressKey($mod) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($mod) | Out-Null; Start-Sleep -Milliseconds 300 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { TypeStr $cmd; Key 0x0D }
Combo2 0x11 0x12 0x72; Start-Sleep 3                                   # Ctrl+Alt+F3 (still logged in)
Run 'cd /usr/share/eternity/shell; sudo curl -fsSO http://172.27.64.1:8790/usr/share/eternity/shell/Consent.qml; grep -c onReturnPressed Consent.qml; pkill quickshell; sleep 2; sudo chvt 7'
Start-Sleep 12; Shot 'k-replayed'
Key 0x0D; Start-Sleep 2; Shot 'k-allowed'                              # Enter = Allow
Start-Sleep 25; Shot 'k-answer-25s'
Start-Sleep 30; Shot 'k-answer-55s'
Start-Sleep 30; Shot 'k-answer-85s'
"done $(Get-Date -Format HH:mm:ss)"

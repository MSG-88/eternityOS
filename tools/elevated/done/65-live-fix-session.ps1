# Build 14 VM sits in a default-config Hyprland session. From a VT: fetch the fixed
# eternity-session from the host, go back, exit Hyprland (default bind Super+M), log in again at
# the greeter and screenshot the real session. Shots: tests\out\hyperv\f-*.png
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
$t0 = Get-Date
Combo2 0x11 0x12 0x72; Start-Sleep 3                                   # Ctrl+Alt+F3
Run 'eternity'; Start-Sleep 3; Run 'eternity'; Start-Sleep 4; Shot 'f-vt'
Run 'cd /usr/local/bin; sudo curl -fsSO http://172.27.64.1:8790/usr/local/bin/eternity-session; grep -c HYPRLAND_CONFIG eternity-session; sudo chvt 7'
Start-Sleep 8; Shot 'f-back'
Combo 0x5B 0x4D; Start-Sleep 6; Shot 'f-greeter'                      # Super+M: exit the default-config Hyprland
foreach ($ch in 'eternity'.ToCharArray()) { Key ([int][char]::ToUpper($ch)) }
Key 0x0D
Start-Sleep 20; Shot 'f-session-20s'
Start-Sleep 25; Shot 'f-session-45s'
Key 0x1B; Start-Sleep 3; Shot 'f-desktop'
"done $(Get-Date -Format HH:mm:ss)"

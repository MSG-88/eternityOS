# From the VT (still logged in): confirm the patched launcher, restart lightdm, log in at the
# greeter with the fixed session and screenshot it. Shots: tests\out\hyperv\g-*.png
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 110 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 60; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 60; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 110 }
function Combo2([int]$m1, [int]$m2, [int]$code) { $k = Kbd; $k.PressKey($m1) | Out-Null; $k.PressKey($m2) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($m2) | Out-Null; $k.ReleaseKey($m1) | Out-Null; Start-Sleep -Milliseconds 400 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { TypeStr $cmd; Key 0x0D }
Combo2 0x11 0x12 0x72; Start-Sleep 3                                   # Ctrl+Alt+F3
Run 'clear; grep -n HYPRLAND_CONFIG /usr/local/bin/eternity-session; free -m; systemctl is-active lightdm; ls /tmp/.X11-unix /run/user/1000 2>/dev/null | head'
Start-Sleep 4; Shot 'g-vt'
Run 'sudo systemctl restart lightdm'
Start-Sleep 15; Combo2 0x11 0x12 0x76; Start-Sleep 4; Shot 'g-greeter'   # Ctrl+Alt+F7
foreach ($ch in 'eternity'.ToCharArray()) { Key ([int][char]::ToUpper($ch)) }
Key 0x0D
Start-Sleep 20; Shot 'g-session-20s'
Start-Sleep 25; Shot 'g-session-45s'
Key 0x1B; Start-Sleep 3; Shot 'g-desktop'
"done $(Get-Date -Format HH:mm:ss)"

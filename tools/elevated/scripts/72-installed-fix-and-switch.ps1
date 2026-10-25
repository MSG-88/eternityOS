# Installed system, XFCE session: apply the launcher + consent fixes persistently, confirm the
# Claude login, make Eternity the default session, restart lightdm, log in. Shots: tests\out\hyperv\n-*.png
param([string]$Password = 'eternity2026!', [string]$HostIp = '172.24.208.1')
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
Add-Type -AssemblyName System.Drawing
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 110 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 60; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 60; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 110 }
function Combo2([int]$m1, [int]$m2, [int]$code) { $k = Kbd; $k.PressKey($m1) | Out-Null; $k.PressKey($m2) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($m2) | Out-Null; $k.ReleaseKey($m1) | Out-Null; Start-Sleep -Milliseconds 400 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function Bright([string]$n) { $bmp = New-Object System.Drawing.Bitmap (Join-Path $Shots "$n.png"); $sum = 0; for ($y = 100; $y -lt 1000; $y += 60) { for ($x = 100; $x -lt 1800; $x += 60) { $c = $bmp.GetPixel($x, $y); $sum += $c.R + $c.G + $c.B } }; $bmp.Dispose(); return $sum }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } '=' { Key 0xBB } '[' { Key 0xDB } ']' { Key 0xDD } '*' { Shifted 0x38 } '|' { Shifted 0xDC } '\' { Key 0xDC } "'" { Key 0xDE } '!' { Shifted 0x31 } ',' { Key 0xBC } '?' { Shifted 0xBF } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { TypeStr $cmd; Key 0x0D }
$H = "http://${HostIp}:8790"
Combo2 0x11 0x12 0x54; Start-Sleep 6                                   # Ctrl+Alt+T: XFCE terminal
$k = Kbd; $k.PressKey(0x11) | Out-Null; $k.TypeKey(0x43) | Out-Null; $k.ReleaseKey(0x11) | Out-Null; Start-Sleep 1   # Ctrl+C clears leftovers
Run 'sudo -v'; Start-Sleep 4; TypeStr $Password; Key 0x0D; Start-Sleep 3
Run "cd /usr/local/bin; sudo curl -fsSO $H/usr/local/bin/eternity-session; cd /usr/share/eternity/shell; sudo curl -fsSO $H/usr/share/eternity/shell/Consent.qml; grep -c HYPRLAND_CONFIG /usr/local/bin/eternity-session; grep -c onReturnPressed Consent.qml; whoami; claude auth status; df -h / | tail -n 1"
Start-Sleep 12; Shot 'n-fetched'
Run "printf '[Seat:*]\nuser-session=eternity\n' | sudo tee /etc/lightdm/lightdm.conf.d/20-session.conf; cat /etc/lightdm/lightdm.conf.d/20-session.conf"
Start-Sleep 6; Shot 'n-conf'
Run 'sudo systemctl restart lightdm'
Start-Sleep 20
$found = $null
foreach ($vt in @(@('F7', 0x76), @('F8', 0x77), @('F1', 0x70), @('F9', 0x78))) {
  Combo2 0x11 0x12 $vt[1]; Start-Sleep 4; Shot ("n-" + $vt[0]); $b = Bright ("n-" + $vt[0]); "brightness " + $vt[0] + ": $b"
  if ($b -gt 2000) { $found = $vt[0]; break }
}
"greeter VT: $found"
Start-Sleep 2; TypeStr $Password; Shot 'n-typed'; Key 0x0D
Start-Sleep 30; Shot 'n-session-30s'
Start-Sleep 20; Key 0x1B; Start-Sleep 3; Shot 'n-desktop'
"done $(Get-Date -Format HH:mm:ss)"

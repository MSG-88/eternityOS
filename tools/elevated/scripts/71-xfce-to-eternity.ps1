# From the running XFCE Classic session: fetch the fixed launcher and consent card from the host,
# make Eternity the greeter's default session, restart lightdm, log in, screenshot the session.
# Runs directly (Hyper-V Administrators). Shots: tests\out\hyperv\x-*.png
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } '=' { Key 0xBB } '[' { Key 0xDB } ']' { Key 0xDD } '*' { Shifted 0x38 } '|' { Shifted 0xDC } "'" { Key 0xDE } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { TypeStr $cmd; Key 0x0D }
$H = 'http://172.27.64.1:8790'
Key 0x1B; Start-Sleep 2                                                # close the first-run wizard
Combo2 0x11 0x12 0x54; Start-Sleep 6                                   # Ctrl+Alt+T: XFCE terminal
Run "cd /usr/local/bin; sudo curl -fsSO $H/usr/local/bin/eternity-session; cd /usr/share/eternity/shell; sudo curl -fsSO $H/usr/share/eternity/shell/Consent.qml; grep -c HYPRLAND_CONFIG /usr/local/bin/eternity-session; grep -c onReturnPressed Consent.qml"
Start-Sleep 8; Shot 'x-fetched'
Run "printf '[Seat:*]\nuser-session=eternity\n' | sudo tee /etc/lightdm/lightdm.conf.d/20-session.conf; sleep 2; sudo systemctl restart lightdm"
Start-Sleep 18
$found = $null
foreach ($vt in @(@('F7', 0x76), @('F8', 0x77), @('F1', 0x70), @('F9', 0x78))) {
  Combo2 0x11 0x12 $vt[1]; Start-Sleep 4; Shot ("x-" + $vt[0]); $b = Bright ("x-" + $vt[0]); "brightness " + $vt[0] + ": $b"
  if ($b -gt 2000) { $found = $vt[0]; break }
}
"greeter VT: $found"
foreach ($ch in 'eternity'.ToCharArray()) { Key ([int][char]::ToUpper($ch)) }
Shot 'x-typed'; Key 0x0D
Start-Sleep 25; Shot 'x-session-25s'
Start-Sleep 20; Key 0x1B; Start-Sleep 3; Shot 'x-desktop'
"done $(Get-Date -Format HH:mm:ss)"

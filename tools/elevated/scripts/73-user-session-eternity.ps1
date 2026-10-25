# Installed system, XFCE session: make Eternity the user's remembered session (lightdm honours
# ~/.dmrc and AccountsService over the seat default), restart lightdm, log in, screenshot.
param([string]$Password = 'eternity2026!', [string]$User = 'testing')
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } '=' { Key 0xBB } '[' { Key 0xDB } ']' { Key 0xDD } '*' { Shifted 0x38 } '|' { Shifted 0xDC } '\' { Key 0xDC } "'" { Key 0xDE } '!' { Shifted 0x31 } ',' { Key 0xBC } '?' { Shifted 0xBF } '>' { Shifted 0xBE } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { TypeStr $cmd; Key 0x0D }
Combo2 0x11 0x12 0x54; Start-Sleep 6                                   # Ctrl+Alt+T
Run 'sudo -v'; Start-Sleep 4; TypeStr $Password; Key 0x0D; Start-Sleep 3
Run "printf '[Desktop]\nSession=eternity\n' > ~/.dmrc; sudo sed -i 's/^Session=.*/Session=eternity/; s/^XSession=.*/XSession=eternity/' /var/lib/AccountsService/users/$User; cat ~/.dmrc /var/lib/AccountsService/users/$User; grep -c HYPRLAND_CONFIG /usr/local/bin/eternity-session"
Start-Sleep 6; Shot 'u-conf'
Run 'sudo systemctl restart lightdm'
Start-Sleep 20
$found = $null
foreach ($vt in @(@('F7', 0x76), @('F8', 0x77), @('F1', 0x70), @('F9', 0x78))) {
  Combo2 0x11 0x12 $vt[1]; Start-Sleep 4; Shot ("u-" + $vt[0]); $b = Bright ("u-" + $vt[0]); "brightness " + $vt[0] + ": $b"
  if ($b -gt 2000) { $found = $vt[0]; break }
}
"greeter VT: $found"
Start-Sleep 2; TypeStr $Password; Shot 'u-typed'; Key 0x0D
Start-Sleep 30; Shot 'u-session-30s'
Start-Sleep 20; Key 0x1B; Start-Sleep 3; Shot 'u-desktop'
"done $(Get-Date -Format HH:mm:ss)"

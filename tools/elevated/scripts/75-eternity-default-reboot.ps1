# Installed system, XFCE (autologin): make Eternity the session everywhere lightdm looks
# (lightdm.conf user-session + autologin-session, AccountsService, ~/.dmrc), one short command at
# a time with a screenshot after each, then a clean reboot. Shots: tests\out\hyperv\p-*.png
param([string]$Password = 'eternity2026!', [string]$User = 'testing')
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
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } '=' { Key 0xBB } '[' { Key 0xDB } ']' { Key 0xDD } '*' { Shifted 0x38 } '|' { Shifted 0xDC } '\' { Key 0xDC } "'" { Key 0xDE } '!' { Shifted 0x31 } ',' { Key 0xBC } '?' { Shifted 0xBF } '>' { Shifted 0xBE } '~' { Shifted 0xC0 } '$' { Shifted 0x34 } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { TypeStr $cmd; Key 0x0D }
Combo2 0x11 0x12 0x54; Start-Sleep 6                                   # Ctrl+Alt+T
$k = Kbd; $k.PressKey(0x11) | Out-Null; $k.TypeKey(0x43) | Out-Null; $k.ReleaseKey(0x11) | Out-Null; Start-Sleep 1
Run 'sudo -v'; Start-Sleep 4; TypeStr $Password; Key 0x0D; Start-Sleep 3; Shot 'p-sudo'
Run "sudo sed -i 's/^user-session=.*/user-session=eternity/; s/^autologin-session=.*/autologin-session=eternity/' /etc/lightdm/lightdm.conf; grep -n 'session\|autologin' /etc/lightdm/lightdm.conf"
Start-Sleep 5; Shot 'p-lightdm-conf'
Run "sudo sed -i 's/^XSession=.*/XSession=eternity/; s/^Session=.*/Session=eternity/' /var/lib/AccountsService/users/$User; sudo cat /var/lib/AccountsService/users/$User"
Start-Sleep 5; Shot 'p-accounts'
Run "printf '[Desktop]\nSession=eternity\n' > ~/.dmrc; cat ~/.dmrc; grep -c HYPRLAND_CONFIG /usr/local/bin/eternity-session; grep -c onReturnPressed /usr/share/eternity/shell/Consent.qml"
Start-Sleep 5; Shot 'p-dmrc'
Run 'sudo reboot'
Start-Sleep 75; Shot 'p-after-reboot'
Start-Sleep 20; Shot 'p-after-reboot2'
"done $(Get-Date -Format HH:mm:ss)"

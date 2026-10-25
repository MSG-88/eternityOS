# Patch the running live session with the four changed files served by the host on port 8790
# (scoped firewall rule for the Default Switch subnet), re-render, reload Hyprland, restart the
# shell, and screenshot. The open terminal in the VM receives the typed commands.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
if (-not (Get-NetFirewallRule -DisplayName 'Eternity dev server 8790' -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName 'Eternity dev server 8790' -Direction Inbound -Protocol TCP -LocalPort 8790 -RemoteAddress 172.27.64.0/20 -Action Allow -Profile Any | Out-Null
  "firewall rule added (TCP 8790 from the Default Switch subnet only)"
}
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 110 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 60; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 60; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 110 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { $k = Kbd; $k.PressKey(0x11) | Out-Null; $k.TypeKey(0x43) | Out-Null; $k.ReleaseKey(0x11) | Out-Null; Start-Sleep -Milliseconds 300; TypeStr $cmd; Key 0x0D }   # Ctrl+C clears leftovers first
$H = 'http://172.27.64.1:8790'
$k = Kbd; $k.PressKey(0x5B) | Out-Null; $k.TypeKey(0x0D) | Out-Null; $k.ReleaseKey(0x5B) | Out-Null; Start-Sleep 6   # Super+Enter: terminal
Run "cd /usr/share/eternity/shell; sudo curl -fsSO $H/usr/share/eternity/shell/Mobius.qml; echo mobius rc"
Run "cd /usr/share/eternity; sudo curl -fsSO $H/usr/share/eternity/hyprland.base.conf; echo template rc"
Run "cd /usr/lib/eternity/py/eternity; sudo curl -fsSO $H/usr/lib/eternity/py/eternity/theme.py; echo theme rc"
Run "cd /usr/local/bin; sudo curl -fsSO $H/usr/local/bin/eternity-session; cd; ls -la /usr/share/eternity/shell/Mobius.qml /usr/share/eternity/hyprland.base.conf"
Start-Sleep 4; Shot 'v2-fetched'
Run "eternity-theme render; hyprctl reload; hyprctl configerrors; sleep 1; pkill quickshell"
Start-Sleep 6; Shot 'v2-reloaded'
Run "exit"
Start-Sleep 8; Shot 'v2-desktop'
Start-Sleep 6; Shot 'v2-desktop2'
"done $(Get-Date -Format HH:mm:ss)"

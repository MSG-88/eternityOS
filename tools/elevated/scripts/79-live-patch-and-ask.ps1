# Installed system, Eternity session: pull the fixed Python modules and Settings page from the host,
# restart the daemon and the shell (eternity-supervise brings both back), then ask Claude again.
# Shots: tests\out\hyperv\lq-*.png
param([string]$Password = 'eternity2026!', [string]$HostIp = '172.24.208.1')
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 100 }
function Shifted([int]$code) { $k = Kbd; $k.PressKey(0x10) | Out-Null; Start-Sleep -Milliseconds 60; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 60; $k.ReleaseKey(0x10) | Out-Null; Start-Sleep -Milliseconds 100 }
function Combo([int]$mod, [int]$code) { $k = Kbd; $k.PressKey($mod) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($mod) | Out-Null; Start-Sleep -Milliseconds 300 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } ':' { Shifted 0xBA } '-' { Key 0xBD } '_' { Shifted 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } ',' { Key 0xBC } '?' { Shifted 0xBF } '|' { Shifted 0xDC } '~' { Shifted 0xC0 } "'" { Key 0xDE } '>' { Shifted 0xBE } '=' { Key 0xBB } '!' { Shifted 0x31 } '&' { Shifted 0x37 } default { if ([char]::IsUpper($ch)) { Shifted ([int]$ch) } else { Key ([int][char]::ToUpper($ch)) } } } } }
function Run([string]$cmd) { TypeStr $cmd; Key 0x0D }
$H = "http://${HostIp}:8790"
$LWIN = 0x5B; $ESC = 0x1B; $RET = 0x0D
Combo $LWIN $RET; Start-Sleep 7                                        # terminal
$k = Kbd; $k.PressKey(0x11) | Out-Null; $k.TypeKey(0x43) | Out-Null; $k.ReleaseKey(0x11) | Out-Null; Start-Sleep 1
Run 'sudo -v'; Start-Sleep 4; TypeStr $Password; Key $RET; Start-Sleep 3
Run "cd /usr/lib/eternity/py/eternity; sudo curl -fsSO $H/usr/lib/eternity/py/eternity/cards.py; sudo curl -fsSO $H/usr/lib/eternity/py/eternity/providers.py; sudo curl -fsSO $H/usr/lib/eternity/py/eternity/settings.py; sudo curl -fsSO $H/usr/lib/eternity/py/eternity/actions.py; sudo curl -fsSO $H/usr/lib/eternity/py/eternity/mcp.py; sudo curl -fsSO $H/usr/lib/eternity/py/eternity/daemon.py; cd /usr/share/eternity/shell; sudo curl -fsSO $H/usr/share/eternity/shell/SettingsContent.qml; grep -c claude_code_model /usr/lib/eternity/py/eternity/cards.py; grep -c wall_ms /usr/lib/eternity/py/eternity/providers.py"
Start-Sleep 25; Shot 'lq-fetched'
Run 'pkill -f eternity-daemon; pkill quickshell; sleep 4; pgrep -af "eternity-daemon|quickshell" | cut -c1-80; exit'
Start-Sleep 10; Shot 'lq-restarted'
Combo $LWIN 0x20; Start-Sleep 2
TypeStr 'Which window manager am I running, what is its version, and how many CPU cores does this machine have?'; Key $RET
Start-Sleep 15; Shot 'lq-15s'
Start-Sleep 25; Shot 'lq-40s'
Start-Sleep 30; Shot 'lq-70s'
Start-Sleep 30; Shot 'lq-100s'
"done $(Get-Date -Format HH:mm:ss)"

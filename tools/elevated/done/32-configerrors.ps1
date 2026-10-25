# In the open terminal of the running session: the full Hyprland config-error list and the
# start-hyprland usage. Shots: tests\out\hyperv\c-*.png
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 120 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } '-' { Key 0xBD } '.' { Key 0xBE } '/' { Key 0xBF } default { Key ([int][char]::ToUpper($ch)) } } } }
TypeStr 'clear; hyprctl configerrors'; Key 0x0D; Start-Sleep 4; Shot 'c-configerrors'
TypeStr 'clear; start-hyprland --help'; Key 0x0D; Start-Sleep 4; Shot 'c-starthyprland'
TypeStr 'clear; grep -n rule /home/eternity/.config/eternity/generated/hyprland.conf; ls /usr/share/eternity/shell/assets'; Key 0x0D; Start-Sleep 4; Shot 'c-rules'
"done $(Get-Date -Format HH:mm:ss)"

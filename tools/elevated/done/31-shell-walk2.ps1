# Walk the running Eternity session with the keyboard: full-res shot, close the wizard, ask bar,
# lock + unlock, terminal with hyprctl output. Shots: tests\out\hyperv\w-*.png (1920x1080).
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 150 }
function Combo([int]$mod, [int]$code) { $k = Kbd; $k.PressKey($mod) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($mod) | Out-Null; Start-Sleep -Milliseconds 300 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function TypeStr([string]$s) { foreach ($ch in $s.ToCharArray()) { switch ($ch) { ' ' { Key 0x20 } ';' { Key 0xBA } '-' { Key 0xBD } default { Key ([int][char]::ToUpper($ch)) } } } }
$VK_LWIN = 0x5B; $VK_ESC = 0x1B; $VK_RET = 0x0D; $VK_SPACE = 0x20
# (resumed: wizard/desktop/ask/lock already captured; the VM sits on the lock screen)
TypeStr 'eternity'; Start-Sleep 1; Shot 'w-lock-typed'; Key $VK_RET; Start-Sleep 5; Shot 'w-unlocked'
Combo $VK_LWIN $VK_RET; Start-Sleep 6; Shot 'w-terminal0'               # Super+Enter
TypeStr 'hyprctl monitors; hyprctl version'; Key $VK_RET; Start-Sleep 4; Shot 'w-terminal'
TypeStr 'ps -o rss comm -C quickshell eternity-daemon Hyprland; hyprctl layers'; Key $VK_RET; Start-Sleep 4; Shot 'w-terminal2'
"done $(Get-Date -Format HH:mm:ss)"

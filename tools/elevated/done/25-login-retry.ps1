# The VM sits at the greeter (Eternity-shell entry). Type the password one key at a time, prove it
# with a screenshot, then log in and screenshot the session as it comes up.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 150 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
$t0 = Get-Date
function At([int]$sec) { $w = $sec - [int]((Get-Date) - $t0).TotalSeconds; if ($w -gt 0) { Start-Sleep -Seconds $w } }
# virtual-key codes: letters are their upper-case ASCII
foreach ($ch in 'eternity'.ToCharArray()) { Key ([int][char]::ToUpper($ch)) }
Shot 'r-typed'
Key 0x0D
At 20; Shot 'r-session-20s'
At 45; Shot 'r-session-45s'
At 80; Shot 'r-session-80s'
"done $(Get-Date -Format HH:mm:ss)"

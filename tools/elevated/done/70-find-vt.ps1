# Find the VT that holds the session (lightdm restarted on another VT), then Enter = Allow.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
Add-Type -AssemblyName System.Drawing
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 110 }
function Combo2([int]$m1, [int]$m2, [int]$code) { $k = Kbd; $k.PressKey($m1) | Out-Null; $k.PressKey($m2) | Out-Null; Start-Sleep -Milliseconds 80; $k.TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 80; $k.ReleaseKey($m2) | Out-Null; $k.ReleaseKey($m1) | Out-Null; Start-Sleep -Milliseconds 400 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function Bright([string]$n) { $bmp = New-Object System.Drawing.Bitmap (Join-Path $Shots "$n.png"); $sum = 0; for ($y = 100; $y -lt 1000; $y += 60) { for ($x = 100; $x -lt 1800; $x += 60) { $c = $bmp.GetPixel($x, $y); $sum += $c.R + $c.G + $c.B } }; $bmp.Dispose(); return $sum }
$found = $null
foreach ($vt in @(@('F8', 0x77), @('F1', 0x70), @('F9', 0x78), @('F2', 0x71), @('F7', 0x76))) {
  Combo2 0x11 0x12 $vt[1]; Start-Sleep 4; Shot ("v-" + $vt[0]); $b = Bright ("v-" + $vt[0]); "brightness " + $vt[0] + ": $b"
  if ($b -gt 2000) { $found = $vt[0]; break }
}
"session VT: $found"
if ($found) { Key 0x0D; Start-Sleep 2; Shot 'v-allowed'; Start-Sleep 30; Shot 'v-answer-30s'; Start-Sleep 30; Shot 'v-answer-60s' }
"done $(Get-Date -Format HH:mm:ss)"

# Build 14 on Hyper-V: recreate the test VM with the new ISO at maximum resources (8 vCPU, up to
# 8 GB so the default local model loads), boot the "Eternity shell" entry, log in key by key, screenshot splash / greeter / session.
# Shots: tests\out\hyperv\b14-*.png (1920x1080). Opens the console for the owner.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Iso = Join-Path $Root 'out\eternity-08-0.1.0-amd64.iso'
$Vhd = Join-Path $Root "out\$VMName.vhdx"
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
New-Item -ItemType Directory -Force $Shots | Out-Null
function Kbd { (Get-WmiObject -Namespace root\virtualization\v2 -Class Msvm_ComputerSystem -Filter "ElementName='$VMName'").GetRelated('Msvm_Keyboard') }
function Key([int]$code) { (Kbd).TypeKey($code) | Out-Null; Start-Sleep -Milliseconds 150 }
function Shot([string]$n) { try { & $shot -VMName $VMName -Path (Join-Path $Shots "$n.png") -Width 1920 -Height 1080 | Out-Null; "shot $n $(Get-Date -Format HH:mm:ss)" } catch { "shot $n failed: $($_.Exception.Message)" } }
function At([int]$sec) { $w = $sec - [int]((Get-Date) - $script:t0).TotalSeconds; if ($w -gt 0) { Start-Sleep -Seconds $w } }

"ISO: $([math]::Round((Get-Item $Iso).Length/1GB,2)) GB, $((Get-Item $Iso).LastWriteTime)"
$vm = Get-VM -Name $VMName -ErrorAction SilentlyContinue
if ($vm) { if ($vm.State -ne 'Off') { Stop-VM -Name $VMName -TurnOff -Force }; Remove-VM -Name $VMName -Force; "old VM removed" }
if (Test-Path $Vhd) { Remove-Item -Force $Vhd }
# Maximum resources on this 8-core / 14 GB host (owner's call: no interruptions): all 8 logical
# CPUs, 4 GB at start growing to 8 GB, high memory priority, CPU weight above every other VM,
# state saved (not lost) if the host stops it, resumed if the host restarts.
New-VM -Name $VMName -Generation 2 -MemoryStartupBytes 4GB -NewVHDPath $Vhd -NewVHDSizeBytes 40GB -SwitchName 'Default Switch' | Out-Null
Set-VM -Name $VMName -ProcessorCount 8 -DynamicMemory -MemoryMinimumBytes 2GB -MemoryMaximumBytes 8GB -AutomaticCheckpointsEnabled $false -CheckpointType Disabled -AutomaticStopAction Save -AutomaticStartAction StartIfRunning -AutomaticStartDelay 30
Set-VMMemory -VMName $VMName -Buffer 25 -Priority 90
Set-VMProcessor -VMName $VMName -Reserve 25 -Maximum 100 -RelativeWeight 200
Set-VMFirmware -VMName $VMName -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
Add-VMDvdDrive -VMName $VMName -Path $Iso
Set-VMFirmware -VMName $VMName -FirstBootDevice (Get-VMDvdDrive -VMName $VMName)
Set-VMVideo -VMName $VMName -ResolutionType Single -HorizontalResolution 1920 -VerticalResolution 1080 -ErrorAction SilentlyContinue
Start-VM -Name $VMName
$script:t0 = Get-Date
"started $t0"
Start-Process -FilePath "$env:windir\System32\vmconnect.exe" -ArgumentList 'localhost', $VMName
At 7;  Key 0x28; Key 0x28; Key 0x28; Shot 'b14-grub'; Key 0x0D     # 4th entry: Eternity shell
At 18; Shot 'b14-splash'
At 30; Shot 'b14-splash2'
At 60; Shot 'b14-login'
foreach ($ch in 'eternity'.ToCharArray()) { Key ([int][char]::ToUpper($ch)) }
Shot 'b14-typed'; Key 0x0D
At 85;  Shot 'b14-session-20s'
At 110; Shot 'b14-session-45s'
Key 0x1B; Start-Sleep 3; Shot 'b14-desktop'                             # Esc closes the first-run wizard
"done $(Get-Date -Format HH:mm:ss)"

# Create (or recreate) the Hyper-V test VM for the current ISO and start it; screenshots of the
# first boot land in tests\out\hyperv\. Gen 2, Secure Boot with the Microsoft UEFI CA template
# (Debian's shim), dynamic memory 3 GB start / 2-6 GB, 4 vCPU, 40 GB disk for install tests.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Iso = Join-Path $Root 'out\eternity-08-0.1.0-amd64.iso'
$Vhd = Join-Path $Root "out\$VMName.vhdx"
$Shots = Join-Path $Root 'tests\out\hyperv'
New-Item -ItemType Directory -Force $Shots | Out-Null
"ISO: $Iso $([math]::Round((Get-Item $Iso).Length/1GB,2)) GB, $((Get-Item $Iso).LastWriteTime)"
"other VMs on this host:"; Get-VM | Select-Object Name, State, @{n='MemGB';e={[math]::Round($_.MemoryAssigned/1GB,1)}} | Format-Table -AutoSize | Out-String

$vm = Get-VM -Name $VMName -ErrorAction SilentlyContinue
if ($vm) { if ($vm.State -ne 'Off') { Stop-VM -Name $VMName -TurnOff -Force }; Remove-VM -Name $VMName -Force; "old $VMName removed" }
if (Test-Path $Vhd) { Remove-Item -Force $Vhd }
New-VM -Name $VMName -Generation 2 -MemoryStartupBytes 3GB -NewVHDPath $Vhd -NewVHDSizeBytes 40GB -SwitchName 'Default Switch' | Out-Null
Set-VM -Name $VMName -ProcessorCount 4 -DynamicMemory -MemoryMinimumBytes 2GB -MemoryMaximumBytes 6GB -AutomaticCheckpointsEnabled $false -CheckpointType Disabled -AutomaticStopAction TurnOff -AutomaticStartAction Nothing
Set-VMFirmware -VMName $VMName -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
Add-VMDvdDrive -VMName $VMName -Path $Iso
Set-VMFirmware -VMName $VMName -FirstBootDevice (Get-VMDvdDrive -VMName $VMName)
Set-VMVideo -VMName $VMName -ResolutionType Single -HorizontalResolution 1920 -VerticalResolution 1080 -ErrorAction SilentlyContinue
"VM $VMName created: Gen2, Secure Boot (Microsoft UEFI CA), dynamic 3 GB (2-6), 4 vCPU, DVD first"
Start-VM -Name $VMName
$t0 = Get-Date
"started $t0"
# the owner's side-by-side console
Start-Process -FilePath "$env:windir\System32\vmconnect.exe" -ArgumentList 'localhost', $VMName
# first-boot screenshots: GRUB (~10 s), splash, greeter (~45 s)
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
foreach ($t in @(12, 30, 60, 90)) {
  $wait = $t - [int]((Get-Date) - $t0).TotalSeconds; if ($wait -gt 0) { Start-Sleep -Seconds $wait }
  try { & $shot -VMName $VMName -Path (Join-Path $Shots "boot-$t.png") | Out-Null; "screenshot boot-$t.png" } catch { "screenshot at $t failed: $($_.Exception.Message)" }
}
"done $(Get-Date)"

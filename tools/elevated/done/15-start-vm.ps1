# Start the test VM with a small startup footprint (host shares memory with WSL and another VM),
# open the console for the owner, screenshot the first boot into tests\out\hyperv\.
$ErrorActionPreference = 'Stop'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
$VMName = 'Eternity08-Test'
$Shots = Join-Path $Root 'tests\out\hyperv'
$shot = Join-Path $Root 'tools\hyperv-screenshot.ps1'
New-Item -ItemType Directory -Force $Shots | Out-Null
"free before: {0:N1} GB" -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)
Set-VM -Name $VMName -DynamicMemory -MemoryStartupBytes 2GB -MemoryMinimumBytes 1GB -MemoryMaximumBytes 6GB
Start-VM -Name $VMName
$t0 = Get-Date
"started $t0"
Start-Process -FilePath "$env:windir\System32\vmconnect.exe" -ArgumentList 'localhost', $VMName
foreach ($t in @(12, 30, 60, 90)) {
  $wait = $t - [int]((Get-Date) - $t0).TotalSeconds; if ($wait -gt 0) { Start-Sleep -Seconds $wait }
  try { & $shot -VMName $VMName -Path (Join-Path $Shots "boot-$t.png") | Out-Null; "screenshot boot-$t.png $(Get-Date -Format HH:mm:ss)" } catch { "screenshot at $t failed: $($_.Exception.Message)" }
}
"memAssigned now: $([math]::Round((Get-VM -Name $VMName).MemoryAssigned/1GB,1)) GB; free: {0:N1} GB" -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)
"done $(Get-Date -Format HH:mm:ss)"

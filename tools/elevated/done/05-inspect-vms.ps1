$ErrorActionPreference = 'Continue'
"host memory: " + ("{0:N1} GB total, {1:N1} GB free" -f ((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB), ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB))
foreach ($vm in Get-VM) {
  "=== $($vm.Name): state=$($vm.State) uptime=$($vm.Uptime) memAssigned=$([math]::Round($vm.MemoryAssigned/1GB,1))GB startup=$([math]::Round($vm.MemoryStartup/1GB,1))GB dynamic=$($vm.DynamicMemoryEnabled) cpus=$($vm.ProcessorCount) gen=$($vm.Generation) created=$($vm.CreationTime)"
  Get-VMDvdDrive -VMName $vm.Name | ForEach-Object { "    dvd: $($_.Path)" }
  Get-VMHardDiskDrive -VMName $vm.Name | ForEach-Object { "    disk: $($_.Path) $(if (Test-Path $_.Path) { [math]::Round((Get-Item $_.Path).Length/1GB,1).ToString() + ' GB' })" }
  "    firmware: secureboot=$((Get-VMFirmware -VMName $vm.Name).SecureBoot) template=$((Get-VMFirmware -VMName $vm.Name).SecureBootTemplate)"
  "    notes: $($vm.Notes)"
}

# Free the test VM's memory without losing the session: save its state (resume with Start-VM).
$ErrorActionPreference = 'Continue'
$vm = Get-VM -Name 'Eternity08-Test'
"before: state=$($vm.State) assigned=$([math]::Round($vm.MemoryAssigned/1GB,1)) GB; host free {0:N1} GB" -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)
if ($vm.State -eq 'Running') { Save-VM -Name 'Eternity08-Test'; Start-Sleep -Seconds 5 }
Set-VM -Name 'Eternity08-Test' -MemoryMaximumBytes 3GB      # keep it modest next time it runs
"after: state=$((Get-VM -Name 'Eternity08-Test').State); host free {0:N1} GB" -f ((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)

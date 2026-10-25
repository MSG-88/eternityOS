# Save the test VM again for the build (it was resumed and holds 4.3 GB); it resumes after.
$ErrorActionPreference = 'Continue'
$vm = Get-VM -Name 'Eternity08-Test'
"before: state=$($vm.State) assigned=$([math]::Round($vm.MemoryAssigned/1GB,1)) GB"
if ($vm.State -eq 'Running') { Save-VM -Name 'Eternity08-Test'; Start-Sleep -Seconds 6 }
"after: state=$((Get-VM -Name 'Eternity08-Test').State); available {0:N1} GB" -f ((Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue/1024)

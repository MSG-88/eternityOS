# Start build 14 in WSL as soon as the host has room: the owner's hand-made VM "New Virtual
# Machine" (4 GB, cannot boot with its Secure Boot template) is off, or free memory exceeds 5 GB.
# Waits up to 40 minutes, then starts anyway if at least 3.5 GB is free (otherwise reports).
$ErrorActionPreference = 'Continue'
$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
function FreeGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB, 1) }
$t0 = Get-Date
while (((Get-Date) - $t0).TotalMinutes -lt 40) {
  $other = Get-VM -Name 'New Virtual Machine' -ErrorAction SilentlyContinue
  $free = FreeGB
  if (($null -eq $other) -or ($other.State -eq 'Off') -or ($free -ge 5)) { break }
  Start-Sleep -Seconds 30
}
$free = FreeGB
"free memory now: $free GB; other VM: $((Get-VM -Name 'New Virtual Machine' -ErrorAction SilentlyContinue).State)"
if ($free -lt 3.5) { "NOT STARTED: only $free GB free (the build host needs up to 5 GB)"; exit 0 }
& wsl -d Debian -- bash -c "setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/build14.sh >/dev/null 2>&1 < /dev/null &"
Start-Sleep -Seconds 5
"build14 started $(Get-Date -Format HH:mm:ss): " + (& wsl -d Debian -- cat /srv/eternity-build/out/build14-run.log 2>$null | Select-Object -First 1)

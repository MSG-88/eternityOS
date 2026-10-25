# Start build 14 in WSL only when the host really has room: the owner's hand-made VM "New Virtual
# Machine" is off (or gone) AND at least 6 GB is free. Polls for up to 3 hours; never starts
# otherwise (the build grows WSL by about 5 GB, and overcommit has crashed WSL and killed the
# session's helpers before).
$ErrorActionPreference = 'Continue'
function FreeGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB, 1) }
$t0 = Get-Date
while (((Get-Date) - $t0).TotalHours -lt 3) {
  $other = Get-VM -Name 'New Virtual Machine' -ErrorAction SilentlyContinue
  $otherOff = ($null -eq $other) -or ($other.State -eq 'Off')
  if ($otherOff -and (FreeGB) -ge 6) { break }
  Start-Sleep -Seconds 30
}
$free = FreeGB
"free memory now: $free GB; other VM: $((Get-VM -Name 'New Virtual Machine' -ErrorAction SilentlyContinue).State) $(Get-Date -Format HH:mm:ss)"
if (-not $otherOff -or $free -lt 6) { "NOT STARTED: no room (other VM $($other.State), $free GB free)"; exit 0 }
& wsl -d Debian -- bash -c "setsid nohup bash /mnt/c/Users/muthu.MSG/Documents/Claude/eternity-08/tools/dev/build14.sh >/dev/null 2>&1 < /dev/null &"
Start-Sleep -Seconds 5
"build14 started $(Get-Date -Format HH:mm:ss): " + (& wsl -d Debian -- cat /srv/eternity-build/out/build14-run.log 2>$null | Select-Object -First 1)

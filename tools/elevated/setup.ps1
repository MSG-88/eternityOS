# One-time elevated setup for Hyper-V testing (needs one UAC approval). Idempotent.
#   1. the user joins "Hyper-V Administrators" (takes effect at the next logon)
#   2. a scheduled task "Eternity-Elevated" runs tools\elevated\run-queue.ps1 with highest
#      privileges; the unelevated session queues scripts into tools\elevated\queue\ and starts
#      the task, so Hyper-V work never waits for a UAC prompt again
#   3. the queue runs once right now (creates and starts the test VM)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$Here = Join-Path $Root 'tools\elevated'
$log = Join-Path $Here 'out\setup.log'
New-Item -ItemType Directory -Force (Join-Path $Here 'out'), (Join-Path $Here 'queue'), (Join-Path $Here 'done') | Out-Null
Start-Transcript -Path $log -Force | Out-Null
try {
  $me = "$env:USERDOMAIN\$env:USERNAME"
  try { Add-LocalGroupMember -Group 'Hyper-V Administrators' -Member $me -ErrorAction Stop; "added $me to Hyper-V Administrators" }
  catch { if ($_.Exception.Message -match 'already') { "$me already in Hyper-V Administrators" } else { throw } }

  $runner = Join-Path $Here 'run-queue.ps1'
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$runner`""
  $principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Highest
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName 'Eternity-Elevated' -Action $action -Principal $principal -Settings $settings -Force | Out-Null
  "task Eternity-Elevated registered (runs $runner elevated on demand)"

  & $runner
  "setup done $(Get-Date)"
} catch {
  "SETUP FAILED: $($_.Exception.Message)"
} finally {
  Stop-Transcript | Out-Null
}

# Runs every *.ps1 in tools\elevated\queue\ (sorted) with elevated rights, logging each to
# tools\elevated\out\<name>.log, then moves it to tools\elevated\done\. Started by the scheduled
# task "Eternity-Elevated" (see setup.ps1):   schtasks /run /tn Eternity-Elevated
$ErrorActionPreference = 'Continue'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Queue = Join-Path $Here 'queue'; $Out = Join-Path $Here 'out'; $Done = Join-Path $Here 'done'
New-Item -ItemType Directory -Force $Queue, $Out, $Done | Out-Null
$lock = Join-Path $Out 'runner.lock'
if (Test-Path $lock) { $age = (Get-Date) - (Get-Item $lock).LastWriteTime; if ($age.TotalHours -lt 3) { exit 0 } }
Set-Content $lock (Get-Date)
try {
  foreach ($s in (Get-ChildItem $Queue -Filter '*.ps1' | Sort-Object Name)) {
    $logf = Join-Path $Out ($s.BaseName + '.log')
    "=== $($s.Name) started $(Get-Date)" | Set-Content $logf
    try { & $s.FullName *>&1 | Out-File -Append -Encoding utf8 $logf; "=== exit ok $(Get-Date)" | Add-Content $logf }
    catch { "=== FAILED: $($_.Exception.Message) $(Get-Date)" | Add-Content $logf }
    Move-Item -Force $s.FullName (Join-Path $Done ($s.Name))
  }
} finally { Remove-Item -Force $lock -ErrorAction SilentlyContinue }

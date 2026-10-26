$Root = 'C:\Users\muthu.MSG\Documents\Claude\eternity-08'
& (Join-Path $Root 'tools\hyperv-screenshot.ps1') -VMName 'Eternity08-Test' -Path (Join-Path $Root 'tests\out\hyperv\now.png') -Width 1920 -Height 1080 | Out-Null
"shot now $(Get-Date -Format HH:mm:ss); VM state: $((Get-VM -Name 'Eternity08-Test').State)"
"done"

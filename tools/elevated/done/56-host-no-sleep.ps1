# Host: never sleep, never hibernate, never turn the display off while on mains, so the build
# host (WSL) and the Hyper-V test VM are never interrupted. Battery timeouts are left alone.
$ErrorActionPreference = 'Continue'
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /change disk-timeout-ac 0
"active scheme: " + (powercfg /getactivescheme)
"AC standby/hibernate/monitor timeouts set to 0 (never) $(Get-Date -Format HH:mm:ss)"
# Hyper-V: make sure the host does not throttle the VM's CPU on power saving
powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100 2>$null
powercfg /setactive SCHEME_CURRENT 2>$null
"processor minimum state on AC: 100%"

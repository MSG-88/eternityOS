# The Hyper-V Default Switch gets a new subnet on every host boot: re-scope the dev-server rule.
$ErrorActionPreference = 'Continue'
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Default Switch*' } | Select-Object -First 1)
if (-not $ip) { "no Default Switch address"; exit 0 }
$o = $ip.IPAddress.Split('.'); $subnet = "$($o[0]).$($o[1]).$([int]$o[2] -band 0xF0).0/20"
Set-NetFirewallRule -DisplayName 'Eternity dev server 8790' -RemoteAddress $subnet
"rule re-scoped to $subnet (host $($ip.IPAddress)) $(Get-Date -Format HH:mm:ss)"

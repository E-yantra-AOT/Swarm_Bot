# start_swarm.ps1
# Launches both swarm bots in separate terminal windows.
# Run from anywhere: .\start_swarm.ps1
# Add -NoStream to skip the live feed: .\start_swarm.ps1 -NoStream

param(
    [switch]$NoStream,
    [string]$IpA = "10.188.41.74",
    [string]$IpB = "10.188.41.184"
)

# Auto-resolve mDNS if available on local network
try {
    $resolvedA = (Resolve-DnsName -Name "pi.local" -Type A -ErrorAction SilentlyContinue).IPAddress | Select-Object -First 1
    if ($resolvedA) { $IpA = $resolvedA }
} catch {}

try {
    $resolvedB = (Resolve-DnsName -Name "pi2.local" -Type A -ErrorAction SilentlyContinue).IPAddress | Select-Object -First 1
    if ($resolvedB) { $IpB = $resolvedB }
} catch {}

$streamFlag = if ($NoStream) { "" } else { "--stream" }

$cmdA = "ssh -o StrictHostKeyChecking=no pi@$IpA " +
        "`"PYTHONUNBUFFERED=1 ~/swarm_venv/bin/python ~/swarm_bot.py --id A $streamFlag`""

$cmdB = "ssh -o StrictHostKeyChecking=no pi2@$IpB " +
        "`"PYTHONUNBUFFERED=1 ~/swarm_venv/bin/python ~/swarm_bot.py --id B $streamFlag`""

Write-Host "Starting Robot A ($IpA)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmdA

Start-Sleep -Milliseconds 500   # Slight delay so A connects first

Write-Host "Starting Robot B ($IpB)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmdB

Write-Host ""
Write-Host "Both robots launched in separate windows!" -ForegroundColor Yellow
if (-not $NoStream) {
    Write-Host "Stream A: http://$($IpA):5000" -ForegroundColor Cyan
    Write-Host "Stream B: http://$($IpB):5000" -ForegroundColor Green
}
Write-Host "Close each window (or Ctrl+C inside it) to stop that robot."

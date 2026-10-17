# Start (or restart) the public POST /analytics endpoint.
# Runs the FastAPI app locally and publishes it with a Cloudflare quick tunnel,
# then writes the public base URL to .tunnel-url.
#
#   .\up.ps1                 # local http://127.0.0.1:8777  +  https://<random>.trycloudflare.com
#   .\up.ps1 -Port 9000      # different local port (tunnel follows it)

param(
    [int]$Port = 8777,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if ($Restart) {
    Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
        Where-Object { $_.CommandLine -match "tunnel --url http://127.0.0.1:$Port" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object { $_.CommandLine -match "uvicorn api\.index:app.*--port $Port" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

$already = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $already) {
    Start-Process -FilePath "python" -WorkingDirectory $root -WindowStyle Hidden -PassThru -ArgumentList @(
        "-m", "uvicorn", "api.index:app",
        "--host", "127.0.0.1", "--port", "$Port"
    ) | Out-Null
    Write-Host "uvicorn   : http://127.0.0.1:$Port"
} else {
    Write-Host "uvicorn   : already listening on $Port"
}

$tunnelRunning = Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
    Where-Object { $_.CommandLine -match "tunnel --url http://127.0.0.1:$Port" }

if (-not $tunnelRunning) {
    Remove-Item (Join-Path $root ".tunnel-url") -ErrorAction SilentlyContinue
    $out = Join-Path $root "tunnel.out.log"
    $err = Join-Path $root "tunnel.err.log"
    Start-Process -FilePath "cloudflared" -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -ArgumentList @(
        "tunnel", "--url", "http://127.0.0.1:$Port", "--no-autoupdate"
    ) | Out-Null
} else {
    Write-Host "cloudflared: already running for port $Port"
}

$url = $null
foreach ($i in 1..30) {
    Start-Sleep -Seconds 1
    $m = Select-String -Path (Join-Path $root "tunnel.err.log") -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -Last 1
    if ($m) { $url = $m.Matches[0].Value; break }
}

if (-not $url) {
    Write-Error "Tunnel URL not found in tunnel.err.log"
    exit 1
}

$url | Set-Content (Join-Path $root ".tunnel-url")
Write-Host "tunnel    : $url"
Write-Host ""
Write-Host "POST /analytics endpoint:  $url/analytics"

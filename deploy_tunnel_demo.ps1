# deploy_tunnel_demo.ps1
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "   Deploying VAYU to Public Tunnel (Test Run)" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "This script will expose your local servers to the internet using localtunnel."
Write-Host ""

# 1. Start the API Tunnel
Write-Host "[1/2] Exposing Backend API on port 8000..." -ForegroundColor Yellow
$BackendTunnelCommand = 'npx localtunnel --port 8000 --subdomain vayu-api-demo-2026'
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendTunnelCommand -WindowStyle Normal

# Wait for tunnel to establish
Start-Sleep -Seconds 3

# 2. Start the App Tunnel
Write-Host "[2/2] Exposing React Frontend on port 5173..." -ForegroundColor Yellow
$FrontendTunnelCommand = 'npx localtunnel --port 5173 --subdomain vayu-app-demo-2026'
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendTunnelCommand -WindowStyle Normal

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Deployment Test Run Initiated!" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: You must update your frontend/.env file with the following:"
Write-Host "VITE_API_URL=https://vayu-api-demo-2026.loca.lt"
Write-Host "Then restart your Vite frontend server."
Write-Host ""
Write-Host "Your public app link will be: https://vayu-app-demo-2026.loca.lt"
Write-Host "=============================================" -ForegroundColor Cyan

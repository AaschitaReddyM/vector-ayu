# run_vayu.ps1
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "     Starting VAYU Local Environment" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Start the Python FastAPI Backend
Write-Host "[1/2] Starting FastAPI Backend on port 8000..." -ForegroundColor Yellow
$BackendCommand = 'python -m uvicorn pre_build.api.main:app --reload'
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCommand -WindowStyle Normal

# Wait a couple of seconds to ensure backend starts first
Start-Sleep -Seconds 3

# 2. Start the React/Vite Frontend
Write-Host "[2/2] Starting React Frontend..." -ForegroundColor Yellow
$FrontendCommand = 'cd frontend; npm install; npm run dev'
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCommand -WindowStyle Normal

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "All services have been launched!" -ForegroundColor Green
Write-Host "Two new terminal windows should have opened."
Write-Host ""
Write-Host "Backend API Swagger Docs : http://127.0.0.1:8000/docs"
Write-Host "Frontend Web Application : Check the frontend window for the localhost URL"
Write-Host "=============================================" -ForegroundColor Cyan

# Script để chạy app với Python 3.12 venv
# Sử dụng script này thay vì run.ps1 sau khi setup Python 3.12

Write-Host "Starting Chat App with Python 3.12..." -ForegroundColor Cyan
Write-Host ""

# Kiểm tra venv312 có tồn tại không
if (-not (Test-Path "venv312\Scripts\Activate.ps1")) {
    Write-Host "ERROR: venv312 not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run setup_python312.ps1 first:" -ForegroundColor Yellow
    Write-Host "  .\setup_python312.ps1" -ForegroundColor White
    exit 1
}

# Activate venv312
Write-Host "Activating Python 3.12 virtual environment..." -ForegroundColor Yellow
& "venv312\Scripts\Activate.ps1"

# Kiểm tra backend
Write-Host "Checking backend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Backend is running" -ForegroundColor Green
} catch {
    Write-Host "⚠ Backend not running. Please start it first:" -ForegroundColor Yellow
    Write-Host "  docker-compose up -d backend" -ForegroundColor White
    Write-Host ""
}

Write-Host ""
Write-Host "Starting app..." -ForegroundColor Cyan
Write-Host ""

# Chạy app
python -m app.main


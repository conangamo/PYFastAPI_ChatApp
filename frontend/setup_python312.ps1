# Script để setup Python 3.12 environment cho Chat App
# Chạy script này sau khi đã cài Python 3.12

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Python 3.12 Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Kiểm tra Python 3.12
Write-Host "Checking Python 3.12..." -ForegroundColor Yellow
$python312 = Get-Command py -ErrorAction SilentlyContinue
if (-not $python312) {
    Write-Host "ERROR: Python launcher (py) not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.12.7 from:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/release/python-3127/" -ForegroundColor Cyan
    exit 1
}

# Kiểm tra Python 3.12 có sẵn không
$pythonVersion = py -3.12 --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python 3.12 not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.12.7 from:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/release/python-3127/" -ForegroundColor Cyan
    exit 1
}

Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
Write-Host ""

# Xóa venv cũ nếu có
if (Test-Path "venv312") {
    Write-Host "Removing old venv312..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force venv312
    Write-Host "✓ Old venv removed" -ForegroundColor Green
    Write-Host ""
}

# Tạo venv mới với Python 3.12
Write-Host "Creating new virtual environment with Python 3.12..." -ForegroundColor Yellow
py -3.12 -m venv venv312
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Virtual environment created" -ForegroundColor Green
Write-Host ""

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv312\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip
Write-Host "✓ pip upgraded" -ForegroundColor Green
Write-Host ""

# Cài đặt packages từ requirements.txt
Write-Host "Installing packages from requirements.txt..." -ForegroundColor Yellow
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install packages" -ForegroundColor Red
    exit 1
}
Write-Host "✓ All packages installed" -ForegroundColor Green
Write-Host ""

# Verify critical packages
Write-Host "Verifying critical packages..." -ForegroundColor Yellow
python -c "import cv2; print(f'✓ OpenCV: {cv2.__version__}')"
python -c "import aiortc; print(f'✓ aiortc: {aiortc.__version__}')"
python -c "import flet; print(f'✓ Flet: {flet.__version__}')"
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the app:" -ForegroundColor Yellow
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  .\venv312\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python -m app.main" -ForegroundColor White
Write-Host ""


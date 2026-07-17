# Starts the FastAPI backend on http://localhost:8000
# Uses `python -m uvicorn` (not the uvicorn.exe shim) so the "&" in the user
# path (C:\Users\R&D) can't break script execution.
$ErrorActionPreference = "Stop"
Set-Location -Path (Join-Path $PSScriptRoot "backend")

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "No virtualenv found. Create it first:" -ForegroundColor Yellow
    Write-Host '  & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv'
    Write-Host '  .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}
if (-not (Test-Path ".\.env")) {
    Write-Host "WARNING: backend\.env not found. Copy .env.example to .env and fill it in." -ForegroundColor Yellow
}

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Green
& .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

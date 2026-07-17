# Starts the Vite dev server on http://localhost:5173
# Invokes vite through node directly instead of `npm run dev`, because npm runs
# scripts via cmd.exe which mis-parses the "&" in the user path (C:\Users\R&D)
# and breaks the node_modules\.bin shims.
$ErrorActionPreference = "Stop"
Set-Location -Path (Join-Path $PSScriptRoot "frontend")

if (-not (Test-Path ".\node_modules\vite\bin\vite.js")) {
    Write-Host "Dependencies not installed. Run: npm install" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
& node ".\node_modules\vite\bin\vite.js"

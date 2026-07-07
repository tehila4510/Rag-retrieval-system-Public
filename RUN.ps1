# Double-click or run:  powershell -ExecutionPolicy Bypass -File RUN.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== RAG Project - Quick Run ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Installing dependencies..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -q

if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "ERROR: Missing .env file!" -ForegroundColor Red
    Write-Host "Run:  Copy-Item .env.example .env" -ForegroundColor Yellow
    Write-Host "Then fill in your real API keys in .env" -ForegroundColor Yellow
    exit 1
}

Remove-Item Env:SSL_CERT_FILE -ErrorAction SilentlyContinue
Remove-Item Env:REQUESTS_CA_BUNDLE -ErrorAction SilentlyContinue
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Running project..." -ForegroundColor Green
.\.venv\Scripts\python.exe run_project.py

Write-Host ""
Write-Host "Done! Output saved to run_output.txt" -ForegroundColor Green
Read-Host "Press Enter to close"

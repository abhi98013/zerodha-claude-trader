# Start Backend Server
Write-Host "Starting Zerodha Claude AI Trader Backend..." -ForegroundColor Cyan
Set-Location backend
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from example. Edit backend/.env with your API keys." -ForegroundColor Yellow
}
New-Item -ItemType Directory -Force -Path logs | Out-Null
pip install -r requirements.txt -q
python main.py

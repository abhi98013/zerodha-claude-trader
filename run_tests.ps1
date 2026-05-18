# Zerodha Claude Trader - Test Runner
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Zerodha Claude AI Trader Test Suite  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Set-Location backend

Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -q

Write-Host "`n[2/3] Creating logs directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path logs | Out-Null

Write-Host "`n[3/3] Running full test suite..." -ForegroundColor Yellow
Write-Host ""

python -m pytest tests/ -v --tb=short --color=yes `
  --junit-xml=test-results.xml `
  -p no:warnings

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "   ALL TESTS PASSED ✅                 " -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "   SOME TESTS FAILED ❌               " -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

Set-Location ..
exit $exitCode

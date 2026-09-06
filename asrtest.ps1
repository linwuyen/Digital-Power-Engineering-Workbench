param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

Write-Host "ASR5K Workbench execution entrypoint is deprecated." -ForegroundColor Yellow
Write-Host "Workbench is now the View / Analysis Plane." -ForegroundColor Yellow
Write-Host "Production build / flash / HIL / qualification execution belongs to:" -ForegroundColor Yellow
Write-Host "  linwuyen/ASR5K_v2_28384" -ForegroundColor Cyan
Write-Host ""
Write-Host "Use the firmware repository's supported tools, for example:" -ForegroundColor White
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_cpu1_headless.ps1"
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File tools/qualify_cpu1_exact_head.ps1 -ExpectedSha <SHA> -Configuration FLASH"
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File tools/build_m0_headless.ps1"
Write-Host ""
Write-Host "See engineering_data/federation/deprecation_registry.json and docs/THREE_REPO_CONVERGENCE.md."
exit 2

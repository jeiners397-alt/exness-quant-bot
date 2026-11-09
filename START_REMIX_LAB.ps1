# Lanza un lote del laboratorio V4 (selecciona hipotesis registradas, max 20). Solo Strategy Tester en la instancia aislada.
# No toca el terminal principal de Exness. Uso: powershell -ExecutionPolicy Bypass -File .\START_REMIX_LAB.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path "C:\REMIX_MT5_LAB\terminal\terminal64.exe")) { Write-Error "Falta la instancia aislada C:\REMIX_MT5_LAB\terminal"; exit 1 }
python -m automation.isolate_lab_terminal | Out-Null   # garantiza: sin cuenta, sin graficos con EAs (salvo login de demo vacia definido por el usuario)
python -m pytest -q tests
if ($LASTEXITCODE -ne 0) { Write-Error "Pruebas unitarias fallidas: lote cancelado"; exit 1 }
python -m automation.autonomous_lab

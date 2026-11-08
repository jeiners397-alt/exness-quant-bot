$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "[1] Preparando entorno local Windows / MetaTrader 5"
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host "[2] Ejecutando pruebas unitarias sin terminal"
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw "Fallo de pruebas unitarias" }
Write-Host "[3] Diagnóstico solo lectura: asegúrate de tener MT5 abierto en cuenta DEMO"
& .\.venv\Scripts\python.exe -m research.mt5_connection
if ($LASTEXITCODE -ne 0) { throw "No se verificó una cuenta DEMO; revisar consola" }
Write-Host "[4] Históricos EURUSDm 14 días M5"
& .\.venv\Scripts\python.exe -m research.data_client --symbol EURUSDm --timeframe M5 --days 14
if ($LASTEXITCODE -ne 0) { throw "La descarga no se completó; consulta symbols_candidates para elegir el símbolo correcto" }
Write-Host "COMPLETO: revisa la carpeta reports/; no se enviaron órdenes."

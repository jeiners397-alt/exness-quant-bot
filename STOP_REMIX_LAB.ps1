# Detiene SOLO la instancia aislada del laboratorio (ejecutable bajo C:\REMIX_MT5_LAB). Nunca el terminal principal de Exness.
Get-CimInstance Win32_Process -Filter "Name='terminal64.exe' or Name='metatester64.exe' or Name='metaeditor64.exe'" |
  Where-Object { $_.ExecutablePath -like "C:\REMIX_MT5_LAB\*" } |
  ForEach-Object { Write-Host "Deteniendo PID $($_.ProcessId) $($_.ExecutablePath)"; Stop-Process -Id $_.ProcessId -Force }
Write-Host "Terminal principal intacto:" (@(Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*MetaTrader 5 EXNESS*" }).Count -gt 0)

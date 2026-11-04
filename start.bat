@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto :directory_error
if not exist ".venv\Scripts\python.exe" goto :missing
".venv\Scripts\python.exe" "scripts\launch.py"
if errorlevel 1 goto :failed
exit /b 0
:missing
echo [FEHLER] Lokale Python-Umgebung fehlt. Bitte zuerst install.bat ausfuehren.
goto :failed
:directory_error
echo [FEHLER] Projektverzeichnis nicht erreichbar.
:failed
echo [FEHLER] Start fehlgeschlagen. Hinweise oben beachten; es wurden keine Pakete installiert.
pause
exit /b 1

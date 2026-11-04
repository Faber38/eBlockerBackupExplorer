@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto :directory_error
if exist ".venv\Scripts\python.exe" goto :existing
py -3 -c "import sys,struct; sys.exit(0 if sys.version_info >= (3,10) and struct.calcsize('P') == 8 else 1)" >nul 2>&1
if not errorlevel 1 goto :launcher
python -c "import sys,struct; sys.exit(0 if sys.version_info >= (3,10) and struct.calcsize('P') == 8 else 1)" >nul 2>&1
if not errorlevel 1 goto :python
echo [FEHLER] Kein geeignetes Python gefunden. Python ab 3.10, 64 Bit erforderlich.
goto :failed
:existing
".venv\Scripts\python.exe" "scripts\install_local.py" --online
goto :result
:launcher
py -3 "scripts\install_local.py" --online
goto :result
:python
python "scripts\install_local.py" --online
:result
if errorlevel 1 goto :failed
echo Installation abgeschlossen. Mit start.bat starten.
pause
exit /b 0
:directory_error
echo [FEHLER] Projektverzeichnis nicht erreichbar.
:failed
echo [FEHLER] Installation nicht abgeschlossen. Hinweise oben und README beachten.
pause
exit /b 1

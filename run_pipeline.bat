@echo off
REM ==============================================================================
REM Lanceur Windows pour le Planificateur de tâches (Task Scheduler)
REM ==============================================================================
cd /d "%~dp0"
set PATH=%USERPROFILE%\.local\bin;%PATH%

echo [%date% %time%] Demarrage du pipeline quotidien automatique... >> logs\scheduler_execution.log
uv run rte-energy >> logs\scheduler_execution.log 2>&1
echo [%date% %time%] Fin de l'execution du pipeline. Code sortie: %ERRORLEVEL% >> logs\scheduler_execution.log


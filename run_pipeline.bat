@echo off
REM ==============================================================================
REM   SCRIPT DE LANCEMENT : run_pipeline.bat
REM   OBJECTIF : Déclenché chaque matin par le Planificateur de Tâches Windows
REM              pour exécuter le pipeline E2E (RTE, Météo, Purge 45j, dbt, IA)
REM ==============================================================================

REM Déplacement dans le répertoire du projet (là où se trouve ce fichier .bat)
cd /d "%~dp0"

REM Inclusion du dossier binaire de uv dans le PATH si nécessaire
set PATH=%USERPROFILE%\.local\bin;%PATH%

REM Création du sous-dossier logs s'il n'existe pas encore
if not exist logs mkdir logs

echo ============================================================================== >> logs\scheduler_execution.log
echo [%date% %time%] Demarrage du pipeline quotidien automatique... >> logs\scheduler_execution.log
echo ============================================================================== >> logs\scheduler_execution.log

REM Exécution du package rte_energy (pipeline unifié avec uv)
if exist "%USERPROFILE%\.local\bin\uv.exe" (
    "%USERPROFILE%\.local\bin\uv.exe" run rte-energy >> logs\scheduler_execution.log 2>&1
) else (
    uv run rte-energy >> logs\scheduler_execution.log 2>&1
)

echo [%date% %time%] Fin de l'execution du pipeline. Code sortie: %ERRORLEVEL% >> logs\scheduler_execution.log
echo. >> logs\scheduler_execution.log

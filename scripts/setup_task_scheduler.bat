@echo off
REM ==============================================================================
REM   CONFIGURATION AUTOMATIQUE DE LA TÂCHE PLANIFIÉE WINDOWS (.BAT)
REM ==============================================================================
REM Ce script enregistre la tâche quotidienne dans le Planificateur Windows.
REM Il résout automatiquement le chemin du projet (parent du dossier scripts).
REM ==============================================================================

echo ====================================================================
echo   CREATION DE LA TACHE PLANIFIEE : RTE_Energy_Daily_Pipeline
echo ====================================================================

set TASK_NAME=RTE_Energy_Daily_Pipeline

REM Résolution dynamique du dossier racine du projet
pushd "%~dp0.."
set PROJECT_DIR=%CD%
popd

set BAT_PATH=%PROJECT_DIR%\run_pipeline.bat

echo 📂 Repertoire du projet : %PROJECT_DIR%
echo ⚙️ Chemin du lanceur    : %BAT_PATH%
echo ⏳ Enregistrement dans le Planificateur Windows (tous les jours a 06:00)...

schtasks /create /tn "%TASK_NAME%" /tr "\"%BAT_PATH%\"" /sc daily /st 06:00 /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ Tache planifiee avec succes !
    echo 📌 Nom de la tache : %TASK_NAME%
    echo 📌 Heure d'execution : Tous les jours a 06:00
    echo 📌 Script lance : %BAT_PATH%
    echo.
    echo Pour verifier son etat :
    echo schtasks /query /tn "%TASK_NAME%"
    echo.
    echo Pour la lancer immediatement pour tester :
    echo schtasks /run /tn "%TASK_NAME%"
) else (
    echo.
    echo ⚠️ Erreur lors de la creation de la tache.
    echo Veuillez executer ce script en tant qu'Administrateur si necessaire.
)

pause

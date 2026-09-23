@echo off
REM ==============================================================================
REM CONFIGURATION AUTOMATIQUE DE LA TÂCHE PLANIFIÉE WINDOWS
REM ==============================================================================
REM Ce script enregistre la tâche quotidienne dans le Planificateur Windows.
REM Il s'exécutera automatiquement chaque jour à 06:00 (ou à la demande).
REM ==============================================================================

echo ====================================================================
echo   CREATION DE LA TACHE PLANIFIEE : RTE_Energy_Daily_Pipeline
echo ====================================================================

set TASK_NAME=RTE_Energy_Daily_Pipeline
set BAT_PATH=e:\Projects\QRA\rte_energie\run_pipeline.bat

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
    echo Pour la lancer immediatement :
    echo schtasks /run /tn "%TASK_NAME%"
) else (
    echo.
    echo ⚠️ Erreur lors de la creation de la tache.
    echo Veuillez executer ce script en tant qu'Administrateur si necessaire.
)

pause

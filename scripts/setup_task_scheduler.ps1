# ==============================================================================
# CONFIGURATION POWERSHELL DE LA TACHE PLANIFIEE WINDOWS
# ==============================================================================

$taskName = "RTE_Energy_Daily_Pipeline"

# Resolution dynamique du dossier racine du projet (dossier parent de 'scripts')
$projectDir = (Get-Item $PSScriptRoot).Parent.FullName
$batPath = Join-Path $projectDir "run_pipeline.bat"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "  CREATION DE LA TACHE PLANIFIEE WINDOWS : $taskName" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "Dossier du projet : $projectDir"
Write-Host "Lanceur Batch     : $batPath"

# 1. Action : lancer run_pipeline.bat dans le dossier racine du projet
$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $projectDir

# 2. Declencheur : Tous les jours a 06:00
$trigger = New-ScheduledTaskTrigger -Daily -At "06:00"

# 3. Parametres avances :
# - StartWhenAvailable : rattrape l'execution si le PC etait eteint a 06:00
# - AllowStartIfOnBatteries : autorise l'execution sur PC portable sur batterie
# - DontStopIfGoingOnBatteries : ne coupe pas si on debranche le chargeur
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# 4. Enregistrement de la tache dans Windows
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Pipeline quotidien : Ingestion RTE, Meteo, Purge 45j, dbt et Inference IA Chronos-Bolt" `
        -Force

    Write-Host "`nTache planifiee avec succes !" -ForegroundColor Green
    Write-Host "Nom de la tache : $taskName"
    Write-Host "Declenchement   : Tous les jours a 06:00 (avec rattrapage automatique si PC eteint)"
    Write-Host "Script execute  : $batPath"
    Write-Host "Dossier travail : $projectDir"
} catch {
    Write-Host "`nErreur lors de l'enregistrement de la tache : $_" -ForegroundColor Red
}

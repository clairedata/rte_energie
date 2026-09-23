# ==============================================================================
# CONFIGURATION POWERSHELL DE LA TÂCHE PLANIFIÉE WINDOWS
# ==============================================================================
# Caractéristique clé : "StartWhenAvailable"
# -> Si le PC était éteint à 06h00, Windows exécute automatiquement la tâche
#    dès que le PC est rallumé !
# ==============================================================================

$taskName = "RTE_Energy_Daily_Pipeline"
$projectDir = "e:\Projects\QRA\rte_energie"
$batPath = Join-Path $projectDir "run_pipeline.bat"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "  CREATION DE LA TACHE PLANIFIEE WINDOWS : $taskName" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

# 1. Action : lancer run_pipeline.bat dans le dossier racine
$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $projectDir

# 2. Déclencheur : Tous les jours à 06:00
$trigger = New-ScheduledTaskTrigger -Daily -At "06:00"

# 3. Paramètres avancés :
# - StartWhenAvailable : rattrape l'exécution si le PC était éteint à 06:00
# - AllowStartIfOnBatteries : autorise l'exécution sur PC portable sur batterie
# - DontStopIfGoingOnBatteries : ne coupe pas si on débranche le chargeur
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# 4. Enregistrement de la tâche
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Ingestion quotidienne RTE, Météo Open-Meteo, transformations dbt et prédictions IA Chronos-Bolt" `
        -Force

    Write-Host "`n✅ Tâche planifiée avec succès !" -ForegroundColor Green
    Write-Host "📌 Nom de la tâche : $taskName"
    Write-Host "📌 Déclenchement : Tous les jours à 06:00 (avec rattrapage automatique si PC éteint)"
    Write-Host "📌 Script exécuté : $batPath"
    Write-Host "`nPour tester l'exécution immédiatement dans le terminal :" -ForegroundColor Yellow
    Write-Host "Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
} catch {
    Write-Host "`n❌ Erreur lors de l'enregistrement de la tâche : $_" -ForegroundColor Red
}

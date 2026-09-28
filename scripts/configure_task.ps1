$task = Get-ScheduledTask -TaskName "RTE_Energy_Daily_Pipeline"
$task.Settings.DisallowStartIfOnBatteries = $false
$task.Settings.StopIfGoingOnBatteries = $false
$task.Settings.StartWhenAvailable = $true
Set-ScheduledTask -InputObject $task
Write-Host "Task settings successfully updated for battery and catch-up!"

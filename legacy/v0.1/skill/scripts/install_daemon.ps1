$ErrorActionPreference = 'Stop'
$TaskName = 'CodexThreadStatus'
$Script = Join-Path $PSScriptRoot 'daemon.py'
$PythonW = (Get-Command pythonw.exe -ErrorAction Stop).Source
$Action = New-ScheduledTaskAction -Execute $PythonW -Argument ('"' + $Script + '"')
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Deterministic Codex thread status title monitor' -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName,State

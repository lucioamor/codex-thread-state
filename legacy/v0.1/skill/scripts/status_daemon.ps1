$Task = Get-ScheduledTask -TaskName 'CodexThreadStatus' -ErrorAction SilentlyContinue
$PidFile = Join-Path $env:USERPROFILE '.codex\thread-status\daemon.pid'
$ProcessId = if (Test-Path -LiteralPath $PidFile) { [int](Get-Content -Raw -LiteralPath $PidFile) } else { $null }
[pscustomobject]@{
  installed = [bool]$Task
  taskState = if ($Task) { $Task.State } else { $null }
  pid = $ProcessId
  processRunning = [bool]($ProcessId -and (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue))
}

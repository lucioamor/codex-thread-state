$ErrorActionPreference = 'Stop'
$TaskName = 'CodexThreadStatus'
$PidFile = Join-Path $env:USERPROFILE '.codex\thread-status\daemon.pid'
if (Test-Path -LiteralPath $PidFile) {
  $ProcessId = [int](Get-Content -Raw -LiteralPath $PidFile)
  Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
[pscustomobject]@{ task = $TaskName; installed = $false }

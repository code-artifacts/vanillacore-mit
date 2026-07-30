[CmdletBinding()]
param(
	[int] $Repetitions = 20,
	[string] $OutputPath
)

Set-StrictMode -Version Latest

if ($Repetitions -le 0) {
	throw 'Repetitions must be positive.'
}
$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-02\results\step-04-scenario-replay.json'
}
$traceDirectory = Join-Path $repositoryRoot 'research\execution\week-02\raw\step-04'
New-Item -ItemType Directory -Force -Path $traceDirectory | Out-Null

& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode `
	"-Dvanillacore.mit.repetitions=$Repetitions" `
	"-Dvanillacore.mit.traceDir=$traceDirectory" `
	'-Dtest=LockTableReplayScenarioTest' test
if ($LASTEXITCODE -ne 0) {
	throw 'Scenario replay failed.'
}

$reportPath = Join-Path $repositoryRoot 'target\surefire-reports\TEST-org.vanilladb.core.storage.tx.concurrency.LockTableReplayScenarioTest.xml'
[xml] $report = Get-Content -LiteralPath $reportPath -Raw
$scenarios = @()
foreach ($id in @('s-s', 's-x', 'x-x', 'reverse-two-resource')) {
	$tracePath = Join-Path $traceDirectory "$id.jsonl"
	$events = @(Get-Content -LiteralPath $tracePath | ForEach-Object {
		$_ | ConvertFrom-Json
	})
	$counts = [ordered]@{}
	foreach ($eventType in @('LOCK_CALL', 'WAIT_BEGIN', 'GRANT', 'RELEASE', 'TX_END')) {
		$counts[$eventType] = @($events | Where-Object event_type -eq $eventType).Count
	}
	$scenarios += [ordered]@{
		id = $id
		repetitions = $Repetitions
		events = $events.Count
		eventCounts = $counts
		traceSha256 = (Get-FileHash -LiteralPath $tracePath -Algorithm SHA256).Hash
		traceLoss = 0
	}
}

$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	repositoryCommit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	traceSchemaVersion = 'vc-locktrace-0'
	scheduler = 'event-conditioned-v0'
	repetitionsPerScenario = $Repetitions
	scenarios = $scenarios
	tests = [ordered]@{
		tests = [int] $report.testsuite.tests
		failures = [int] $report.testsuite.failures
		errors = [int] $report.testsuite.errors
		skipped = [int] $report.testsuite.skipped
	}
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "Scenario replay evidence written to $OutputPath"

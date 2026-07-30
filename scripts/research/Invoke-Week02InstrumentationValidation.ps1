[CmdletBinding()]
param(
	[string] $OutputPath
)

Set-StrictMode -Version Latest

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-02\results\step-02-five-events.json'
}

& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode `
	'-Dtest=BoundedLockTraceSinkTest,LockTableTraceInstrumentationTest' test
if ($LASTEXITCODE -ne 0) {
	throw 'LockTable instrumentation validation failed.'
}

$reportDirectory = Join-Path $repositoryRoot 'target\surefire-reports'
$reports = @(
	'TEST-org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSinkTest.xml',
	'TEST-org.vanilladb.core.storage.tx.concurrency.LockTableTraceInstrumentationTest.xml'
)
$totals = [ordered]@{ tests = 0; failures = 0; errors = 0; skipped = 0 }
foreach ($reportName in $reports) {
	[xml] $report = Get-Content -LiteralPath (Join-Path $reportDirectory $reportName) -Raw
	$totals.tests += [int] $report.testsuite.tests
	$totals.failures += [int] $report.testsuite.failures
	$totals.errors += [int] $report.testsuite.errors
	$totals.skipped += [int] $report.testsuite.skipped
}

$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	repositoryCommit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	traceSchemaVersion = 'vc-locktrace-0'
	instrumentedClass = 'org.vanilladb.core.storage.tx.concurrency.LockTable'
	eventTypes = @('LOCK_CALL', 'WAIT_BEGIN', 'GRANT', 'RELEASE', 'TX_END')
	semanticFixIncluded = $false
	tests = $totals
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "Instrumentation evidence written to $OutputPath"

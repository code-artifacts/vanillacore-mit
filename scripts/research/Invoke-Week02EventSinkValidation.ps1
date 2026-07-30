[CmdletBinding()]
param(
	[string] $OutputPath
)

Set-StrictMode -Version Latest

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-02\results\step-01-event-sink.json'
}

& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode `
	'-Dtest=BoundedLockTraceSinkTest' test
if ($LASTEXITCODE -ne 0) {
	throw 'Event sink validation failed.'
}

$reportPath = Join-Path $repositoryRoot 'target\surefire-reports\TEST-org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSinkTest.xml'
[xml] $report = Get-Content -LiteralPath $reportPath -Raw
$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	repositoryCommit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	traceSchemaVersion = 'vc-locktrace-0'
	sink = [ordered]@{
		type = 'bounded-in-memory'
		nonBlockingProducer = $true
		explicitLossCounter = $true
	}
	tests = [ordered]@{
		tests = [int] $report.testsuite.tests
		failures = [int] $report.testsuite.failures
		errors = [int] $report.testsuite.errors
		skipped = [int] $report.testsuite.skipped
	}
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "Event sink evidence written to $OutputPath"

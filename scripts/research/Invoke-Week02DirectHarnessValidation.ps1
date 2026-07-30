[CmdletBinding()]
param(
	[string] $OutputPath
)

Set-StrictMode -Version Latest

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-02\results\step-03-direct-harness.json'
}

& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode `
	'-Dtest=DirectLockTableHarnessTest' test
if ($LASTEXITCODE -ne 0) {
	throw 'Direct LockTable harness validation failed.'
}

$reportPath = Join-Path $repositoryRoot 'target\surefire-reports\TEST-org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarnessTest.xml'
[xml] $report = Get-Content -LiteralPath $reportPath -Raw
$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	repositoryCommit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	harness = 'DirectLockTableHarness'
	capabilities = @(
		'direct-five-mode-lock',
		'async-lock-request',
		'event-conditioned-wait',
		'specific-release',
		'transaction-end',
		'bounded-trace-snapshot',
		'deterministic-cleanup'
	)
	tests = [ordered]@{
		tests = [int] $report.testsuite.tests
		failures = [int] $report.testsuite.failures
		errors = [int] $report.testsuite.errors
		skipped = [int] $report.testsuite.skipped
	}
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "Direct harness evidence written to $OutputPath"

[CmdletBinding()]
param(
	[string] $OutputPath
)

Set-StrictMode -Version Latest

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-02\results\step-06-g0-g2-decision.json'
}
$week01Results = Join-Path $repositoryRoot 'research\execution\week-01\results'
$week02Results = Join-Path $repositoryRoot 'research\execution\week-02\results'

& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode test
if ($LASTEXITCODE -ne 0) {
	throw 'Current full suite failed.'
}
$fullSuiteReport = Join-Path $repositoryRoot 'target\surefire-reports\TEST-org.vanilladb.core.FullTestSuite.xml'
[xml] $fullSuite = Get-Content -LiteralPath $fullSuiteReport -Raw

$mitTests = @(
	'BoundedLockTraceSinkTest',
	'LockTableTraceInstrumentationTest',
	'DirectLockTableHarnessTest',
	'LockTableReplayScenarioTest'
) -join ','
& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode `
	"-Dtest=$mitTests" test
if ($LASTEXITCODE -ne 0) {
	throw 'Current MIT functional suite failed.'
}

$mitReports = @(
	'TEST-org.vanilladb.core.storage.tx.concurrency.trace.BoundedLockTraceSinkTest.xml',
	'TEST-org.vanilladb.core.storage.tx.concurrency.LockTableTraceInstrumentationTest.xml',
	'TEST-org.vanilladb.core.storage.tx.concurrency.DirectLockTableHarnessTest.xml',
	'TEST-org.vanilladb.core.storage.tx.concurrency.LockTableReplayScenarioTest.xml'
)
$mitTotals = [ordered]@{ tests = 0; failures = 0; errors = 0; skipped = 0 }
foreach ($reportName in $mitReports) {
	[xml] $report = Get-Content -LiteralPath (
			Join-Path $repositoryRoot "target\surefire-reports\$reportName") -Raw
	$mitTotals.tests += [int] $report.testsuite.tests
	$mitTotals.failures += [int] $report.testsuite.failures
	$mitTotals.errors += [int] $report.testsuite.errors
	$mitTotals.skipped += [int] $report.testsuite.skipped
}

$buildMatrix = Get-Content -LiteralPath (
		Join-Path $week01Results 'step-03-build-matrix.json') -Raw |
	ConvertFrom-Json
$repetition = Get-Content -LiteralPath (
		Join-Path $week01Results 'step-04-repetition-summary.json') -Raw |
	ConvertFrom-Json
$pr95 = Get-Content -LiteralPath (
		Join-Path $week01Results 'step-06-pr95-witness-matrix.json') -Raw |
	ConvertFrom-Json
$replay = Get-Content -LiteralPath (
		Join-Path $week02Results 'step-04-scenario-replay.json') -Raw |
	ConvertFrom-Json
$quality = Get-Content -LiteralPath (
		Join-Path $week02Results 'step-05-trace-quality.json') -Raw |
	ConvertFrom-Json

$g0Passed = (
	@($buildMatrix.builds | Where-Object {
		$_.exitCode -ne 0 -or $_.timedOut -or
		$_.tests.failures -ne 0 -or $_.tests.errors -ne 0
	}).Count -eq 0 -and
	@($repetition.campaigns | Where-Object {
		$_.passes -ne $_.repetitionsRequested -or $_.failures -ne 0
	}).Count -eq 0 -and
	[int] $fullSuite.testsuite.failures -eq 0 -and
	[int] $fullSuite.testsuite.errors -eq 0 -and
	$mitTotals.failures -eq 0 -and $mitTotals.errors -eq 0
)
$g1MinimumPassed = (
	$pr95.matrixPassed -and
	$quality.baselineStress.offModeLockOperations -ge 1000000 -and
	$quality.baselineStress.unexplainedPollutedSamples -eq 0
)
$g2Passed = (
	$quality.completeness.microPrecision -ge 0.95 -and
	$quality.completeness.microRecall -ge 0.95 -and
	$quality.completeness.traceLoss -eq 0 -and
	@($replay.scenarios | Where-Object { $_.traceLoss -ne 0 }).Count -eq 0
)
$overallDecision = if ($g0Passed -and $g1MinimumPassed -and $g2Passed) {
	'CONDITIONAL_GO'
} else {
	'NO_GO'
}

$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	repositoryCommit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	decisionScope = 'G0-G2 at the end of Week 2'
	gates = @(
		[ordered]@{
			id = 'G0'
			name = 'Build'
			status = if ($g0Passed) { 'PASS' } else { 'FAIL' }
			evidence = [ordered]@{
				dualBaselineBuilds = $buildMatrix.builds.Count
				freshProcessCampaigns = $repetition.campaigns.Count
				currentFullSuite = [ordered]@{
					tests = [int] $fullSuite.testsuite.tests
					failures = [int] $fullSuite.testsuite.failures
					errors = [int] $fullSuite.testsuite.errors
				}
				currentMitFunctionalSuite = $mitTotals
			}
		},
		[ordered]@{
			id = 'G1'
			name = 'Baseline'
			status = if ($g1MinimumPassed) {
				'CONDITIONAL_PASS'
			} else {
				'FAIL'
			}
			evidence = [ordered]@{
				pr95DifferentialPassed = $pr95.matrixPassed
				offModeLockOperations =
						$quality.baselineStress.offModeLockOperations
				unexplainedPollutedSamples =
						$quality.baselineStress.unexplainedPollutedSamples
			}
			limitations = @(
				'stress workload is single-thread S acquire/release',
				'instrumented main source remains pristine rather than PR95 reference fix',
				'conflicting 2/4/8/16-worker stress matrix remains open'
			)
		},
		[ordered]@{
			id = 'G2'
			name = 'Trace'
			status = if ($g2Passed) {
				'PASS_SCOPE_LIMITED'
			} else {
				'FAIL'
			}
			evidence = [ordered]@{
				microPrecision = $quality.completeness.microPrecision
				microRecall = $quality.completeness.microRecall
				traceLoss = $quality.completeness.traceLoss
				scenarios = $replay.scenarios.Count
				repetitionsPerScenario = $replay.repetitionsPerScenario
			}
			limitations = @(
				'precision and recall cover event-type multiplicity in Direct scenarios',
				'resource role, parent, purpose, and owner/waiter snapshots are not validated',
				'abort is an external Future outcome rather than a v0 trace event'
			)
		}
	)
	performanceRisk = [ordered]@{
		status = if ($quality.overhead.withinHardCeiling) {
			'ACCEPTABLE_FOR_G3'
		} else {
			'BLOCKS_G3'
		}
		lowOverheadPercent = $quality.overhead.lowOverheadPercent
		hardCeilingPercent = $quality.overhead.hardCeilingPercent
	}
	overall = [ordered]@{
		decision = $overallDecision
		allowedNext = @(
			'L1 TLA+ model',
			'trace schema and mapping refinement',
			'Direct harness correctness experiments'
		)
		blockedUntilResolved = @(
			'G3 replay or low-overhead claims',
			'broad mutation campaign',
			'production-performance claims'
		)
		mandatoryActions = @(
			'activate PR95 as a separate reference-fix patch set',
			'run conflicting 2/4/8/16-worker million-operation stress',
			'reduce low overhead to at most 25 percent and remeasure unchanged protocol',
			'add explicit abort and trace-loss semantics before strong refinement verdicts'
		)
	}
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "G0-G2 decision evidence written to $OutputPath"

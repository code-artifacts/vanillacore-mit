[CmdletBinding()]
param(
	[int] $TimeoutSeconds = 180,
	[string] $OutputPath
)

Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'common\JavaToolchain.ps1')

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
$identity = Get-Content -LiteralPath (Join-Path $repositoryRoot 'research\execution\week-01\results\step-02-baselines.json') -Raw |
	ConvertFrom-Json
$patchPath = Join-Path $repositoryRoot $identity.patch.path
$jdk = Resolve-ResearchJavaHome -Major 17
if ($jdk.Vendor -ne 'Eclipse Adoptium' -or $jdk.RuntimeVersion -ne '17.0.20+8') {
	throw "Unexpected JDK: $($jdk.Vendor) $($jdk.RuntimeVersion)"
}
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-01\results\step-06-pr95-witness-matrix.json'
}

$rawDirectory = Join-Path $repositoryRoot 'research\execution\week-01\raw\step-06'
$worktreeRoot = Join-Path ([System.IO.Path]::GetTempPath()) "vanillacore-mit-step06-$PID"
$pristinePath = Join-Path $worktreeRoot 'pristine'
$fixedPath = Join-Path $worktreeRoot 'pr95'
$mavenCommand = (Get-Command mvn.cmd).Source
$witnessFiles = @(
	'src\test\java\org\vanilladb\core\storage\tx\concurrency\LockTableTestProbe.java',
	'src\test\java\org\vanilladb\core\storage\tx\concurrency\LockTablePr95WitnessTest.java'
)

function Copy-WitnessSources {
	param([string] $DestinationRoot)
	foreach ($relativePath in $witnessFiles) {
		$destination = Join-Path $DestinationRoot $relativePath
		New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
		Copy-Item -LiteralPath (Join-Path $repositoryRoot $relativePath) -Destination $destination -Force
	}
}

function Invoke-Witnesses {
	param(
		[string] $Variant,
		[string] $WorkingDirectory
	)

	$stdoutPath = Join-Path $rawDirectory "$Variant.stdout.log"
	$stderrPath = Join-Path $rawDirectory "$Variant.stderr.log"
	$arguments = @(
		'-Pmit-research',
		'--batch-mode',
		'-Dtest=LockTablePr95WitnessTest',
		'-Dvanillacore.mit.pr95Witnesses=true',
		'-Dsurefire.rerunFailingTestsCount=0',
		'test'
	)
	$startedAt = Get-Date
	$process = Start-Process -FilePath $mavenCommand `
		-ArgumentList $arguments `
		-WorkingDirectory $WorkingDirectory `
		-RedirectStandardOutput $stdoutPath `
		-RedirectStandardError $stderrPath `
		-NoNewWindow `
		-PassThru

	$completed = $process.WaitForExit($TimeoutSeconds * 1000)
	if (-not $completed) {
		& taskkill /PID $process.Id /T /F | Out-Null
		$process.WaitForExit()
	}

	$reportPath = Join-Path $WorkingDirectory 'target\surefire-reports\TEST-org.vanilladb.core.storage.tx.concurrency.LockTablePr95WitnessTest.xml'
	$tests = 0
	$failures = 0
	$errors = 0
	$skipped = 0
	if (Test-Path -LiteralPath $reportPath) {
		[xml] $report = Get-Content -LiteralPath $reportPath -Raw
		$tests = [int] $report.testsuite.tests
		$failures = [int] $report.testsuite.failures
		$errors = [int] $report.testsuite.errors
		$skipped = [int] $report.testsuite.skipped
	}

	[ordered]@{
		variant = $Variant
		startedAt = $startedAt.ToString('o')
		durationSeconds = [Math]::Round(((Get-Date) - $startedAt).TotalSeconds, 3)
		timedOut = (-not $completed)
		exitCode = if ($completed) { $process.ExitCode } else { -1 }
		tests = $tests
		failures = $failures
		errors = $errors
		skipped = $skipped
		stdoutSha256 = (Get-FileHash -LiteralPath $stdoutPath -Algorithm SHA256).Hash
		stderrSha256 = (Get-FileHash -LiteralPath $stderrPath -Algorithm SHA256).Hash
		lockTableSha256 = (Get-FileHash -LiteralPath (Join-Path $WorkingDirectory 'src\main\java\org\vanilladb\core\storage\tx\concurrency\LockTable.java') -Algorithm SHA256).Hash
	}
}

$previousJavaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Process')
$previousPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
$pristineAdded = $false
$fixedAdded = $false

try {
	New-Item -ItemType Directory -Force -Path $rawDirectory, $worktreeRoot | Out-Null
	$head = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	$mainTree = (& git -C $repositoryRoot rev-parse 'HEAD:src/main').Trim()
	$upstreamMainTree = (& git -C $repositoryRoot rev-parse "$($identity.upstream.commit):src/main").Trim()
	if ($mainTree -ne $upstreamMainTree) {
		throw 'Production source differs from the pinned upstream baseline.'
	}

	& git -C $repositoryRoot worktree add --detach $pristinePath $head
	if ($LASTEXITCODE -ne 0) {
		throw 'Unable to create pristine witness worktree.'
	}
	$pristineAdded = $true
	& git -C $repositoryRoot worktree add --detach $fixedPath $head
	if ($LASTEXITCODE -ne 0) {
		throw 'Unable to create fixed witness worktree.'
	}
	$fixedAdded = $true

	Copy-WitnessSources -DestinationRoot $pristinePath
	Copy-WitnessSources -DestinationRoot $fixedPath
	& git -C $fixedPath apply --check $patchPath
	if ($LASTEXITCODE -ne 0) {
		throw 'PR #95 patch dry-run failed.'
	}
	& git -C $fixedPath apply $patchPath
	if ($LASTEXITCODE -ne 0) {
		throw 'PR #95 patch application failed.'
	}

	$env:JAVA_HOME = $jdk.Home
	$env:PATH = "$(Join-Path $jdk.Home 'bin');$previousPath"
	$matrix = @(
		Invoke-Witnesses -Variant 'VC-HEAD-20230430' -WorkingDirectory $pristinePath
		Invoke-Witnesses -Variant 'VC-REF-95' -WorkingDirectory $fixedPath
	)

	$matrixPassed = (
		$matrix[0].exitCode -ne 0 -and
		$matrix[0].tests -eq 2 -and
		$matrix[0].failures -eq 2 -and
		$matrix[0].errors -eq 0 -and
		$matrix[1].exitCode -eq 0 -and
		$matrix[1].tests -eq 2 -and
		$matrix[1].failures -eq 0 -and
		$matrix[1].errors -eq 0 -and
		-not $matrix[0].timedOut -and
		-not $matrix[1].timedOut
	)

	$result = [ordered]@{
		schemaVersion = 1
		recordedAt = (Get-Date).ToString('o')
		repositoryCommit = $head
		upstreamCommit = $identity.upstream.commit
		productionSourceMatchesUpstream = $true
		patchSha256 = $identity.patch.sha256
		jdk = $jdk
		witnesses = @(
			'lockerRegistrySupportsUpdatesFromDistinctAnchors',
			'reentrantGrantRemovesWaitRegistration'
		)
		expected = [ordered]@{
			pristineFailures = 2
			referenceFixFailures = 0
		}
		matrix = $matrix
		matrixPassed = $matrixPassed
	}

	$directory = Split-Path -Parent $OutputPath
	New-Item -ItemType Directory -Force -Path $directory | Out-Null
	$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8
	if (-not $matrixPassed) {
		throw "PR #95 witness matrix did not match expectations. Worktrees retained at $worktreeRoot"
	}
} finally {
	if ($null -eq $previousJavaHome) {
		Remove-Item Env:JAVA_HOME -ErrorAction SilentlyContinue
	} else {
		$env:JAVA_HOME = $previousJavaHome
	}
	$env:PATH = $previousPath

	if ($null -ne (Get-Variable result -ErrorAction SilentlyContinue) -and $result.matrixPassed) {
		if ($pristineAdded) {
			& git -C $repositoryRoot worktree remove --force $pristinePath | Out-Null
		}
		if ($fixedAdded) {
			& git -C $repositoryRoot worktree remove --force $fixedPath | Out-Null
		}
		& git -C $repositoryRoot worktree prune
		Remove-Item -LiteralPath $worktreeRoot -Force -Recurse -ErrorAction SilentlyContinue
	}
}

Write-Host "PR #95 witness evidence written to $OutputPath"

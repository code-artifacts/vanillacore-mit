[CmdletBinding()]
param(
	[int] $TimeoutSeconds = 600,
	[string] $OutputPath
)

Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'common\JavaToolchain.ps1')

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
$identityPath = Join-Path $repositoryRoot 'research\execution\week-01\results\step-02-baselines.json'
$identity = Get-Content -LiteralPath $identityPath -Raw | ConvertFrom-Json
$patchPath = Join-Path $repositoryRoot $identity.patch.path
$jdk = Resolve-ResearchJavaHome -Major 17

if ($jdk.Vendor -ne 'Eclipse Adoptium' -or $jdk.RuntimeVersion -ne '17.0.20+8') {
	throw "Unexpected JDK: $($jdk.Vendor) $($jdk.RuntimeVersion)"
}
if ((Get-FileHash -LiteralPath $patchPath -Algorithm SHA256).Hash -ne $identity.patch.sha256) {
	throw 'PR #95 patch hash differs from the baseline manifest.'
}
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-01\results\step-03-build-matrix.json'
}

$rawDirectory = Join-Path $repositoryRoot 'research\execution\week-01\raw\step-03'
$worktreeRoot = Join-Path ([System.IO.Path]::GetTempPath()) "vanillacore-mit-step03-$PID"
$pristinePath = Join-Path $worktreeRoot 'pristine'
$fixedPath = Join-Path $worktreeRoot 'pr95'
$mavenCommand = (Get-Command mvn.cmd).Source

function Invoke-CleanBuild {
	param(
		[string] $Variant,
		[string] $WorkingDirectory
	)

	$stdoutPath = Join-Path $rawDirectory "$Variant.stdout.log"
	$stderrPath = Join-Path $rawDirectory "$Variant.stderr.log"
	$startedAt = Get-Date
	$process = Start-Process -FilePath $mavenCommand `
		-ArgumentList @('--batch-mode', 'clean', 'test') `
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

	$reports = Get-ChildItem -LiteralPath (Join-Path $WorkingDirectory 'target\surefire-reports') `
		-Filter 'TEST-*.xml' -ErrorAction SilentlyContinue
	$totals = [ordered]@{ tests = 0; failures = 0; errors = 0; skipped = 0 }
	foreach ($report in $reports) {
		[xml] $xml = Get-Content -LiteralPath $report.FullName -Raw
		$totals.tests += [int] $xml.testsuite.tests
		$totals.failures += [int] $xml.testsuite.failures
		$totals.errors += [int] $xml.testsuite.errors
		$totals.skipped += [int] $xml.testsuite.skipped
	}

	[ordered]@{
		variant = $Variant
		command = 'mvn --batch-mode clean test'
		startedAt = $startedAt.ToString('o')
		durationSeconds = [Math]::Round(((Get-Date) - $startedAt).TotalSeconds, 3)
		timedOut = (-not $completed)
		exitCode = if ($completed) { $process.ExitCode } else { -1 }
		tests = $totals
		lockTableSha256 = (Get-FileHash -LiteralPath (Join-Path $WorkingDirectory 'src\main\java\org\vanilladb\core\storage\tx\concurrency\LockTable.java') -Algorithm SHA256).Hash
	}
}

$previousJavaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Process')
$previousPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
$pristineAdded = $false
$fixedAdded = $false

try {
	New-Item -ItemType Directory -Force -Path $rawDirectory, $worktreeRoot | Out-Null
	& git -C $repositoryRoot worktree add --detach $pristinePath $identity.upstream.commit
	if ($LASTEXITCODE -ne 0) {
		throw 'Unable to create pristine worktree.'
	}
	$pristineAdded = $true

	& git -C $repositoryRoot worktree add --detach $fixedPath $identity.upstream.commit
	if ($LASTEXITCODE -ne 0) {
		throw 'Unable to create PR #95 worktree.'
	}
	$fixedAdded = $true

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

	$builds = @(
		Invoke-CleanBuild -Variant 'VC-HEAD-20230430' -WorkingDirectory $pristinePath
		Invoke-CleanBuild -Variant 'VC-REF-95' -WorkingDirectory $fixedPath
	)

	$result = [ordered]@{
		schemaVersion = 1
		recordedAt = (Get-Date).ToString('o')
		upstreamCommit = $identity.upstream.commit
		patchSha256 = $identity.patch.sha256
		jdk = $jdk
		mavenVersion = (& mvn -version 2>&1 | Select-Object -First 1)
		timeoutSeconds = $TimeoutSeconds
		builds = $builds
	}

	$directory = Split-Path -Parent $OutputPath
	New-Item -ItemType Directory -Force -Path $directory | Out-Null
	$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8

	$failed = @($builds | Where-Object {
		$_.timedOut -or $_.exitCode -ne 0 -or $_.tests.failures -ne 0 -or $_.tests.errors -ne 0
	})
	if ($failed.Count -gt 0) {
		throw "One or more baseline builds failed. Worktrees retained at $worktreeRoot"
	}
} finally {
	if ($null -eq $previousJavaHome) {
		Remove-Item Env:JAVA_HOME -ErrorAction SilentlyContinue
	} else {
		$env:JAVA_HOME = $previousJavaHome
	}
	$env:PATH = $previousPath

	if ($null -ne (Get-Variable result -ErrorAction SilentlyContinue)) {
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

Write-Host "Dual-baseline build evidence written to $OutputPath"

[CmdletBinding()]
param(
	[int] $Repetitions = 20,
	[int] $TimeoutSeconds = 420,
	[string] $SummaryPath,
	[string] $RunsPath
)

Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'common\JavaToolchain.ps1')

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
$jdk = Resolve-ResearchJavaHome -Major 17
if ($jdk.Vendor -ne 'Eclipse Adoptium' -or $jdk.RuntimeVersion -ne '17.0.20+8') {
	throw "Unexpected JDK: $($jdk.Vendor) $($jdk.RuntimeVersion)"
}
if (-not $SummaryPath) {
	$SummaryPath = Join-Path $repositoryRoot 'research\execution\week-01\results\step-04-repetition-summary.json'
}
if (-not $RunsPath) {
	$RunsPath = Join-Path $repositoryRoot 'research\execution\week-01\results\step-04-runs.csv'
}

$rawRoot = Join-Path $repositoryRoot 'research\execution\week-01\raw\step-04'
$templatePath = Join-Path $repositoryRoot 'src\test\resources\org\vanilladb\core\vanilladb.properties'
$reportsPath = Join-Path $repositoryRoot 'target\surefire-reports'
$mavenCommand = (Get-Command mvn.cmd).Source
$campaigns = @(
	[ordered]@{
		id = 'default-suite'
		selector = 'FullTestSuite'
		expectedTests = 110
	},
	[ordered]@{
		id = 'omitted-five'
		selector = 'ParserTest,SpResultSetTest,ConstantRangeTest,ConstantTest,BTreeIndexConcurrentTest'
		expectedTests = 10
	}
)

function Remove-SurefireReports {
	$root = [System.IO.Path]::GetFullPath($repositoryRoot).TrimEnd('\') + '\'
	$target = [System.IO.Path]::GetFullPath($reportsPath)
	if (-not $target.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
		throw "Refusing to remove reports outside repository: $target"
	}
	if (Test-Path -LiteralPath $target) {
		Remove-Item -LiteralPath $target -Recurse -Force
	}
}

function Reset-RunDirectory {
	param([string] $RunDirectory)

	$root = [System.IO.Path]::GetFullPath($rawRoot).TrimEnd('\') + '\'
	$target = [System.IO.Path]::GetFullPath($RunDirectory)
	if (-not $target.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
		throw "Refusing to reset run directory outside raw root: $target"
	}
	if (Test-Path -LiteralPath $target) {
		Remove-Item -LiteralPath $target -Recurse -Force
	}
	New-Item -ItemType Directory -Force -Path $target | Out-Null
}

function New-IsolatedConfig {
	param(
		[string] $RunDirectory
	)

	$storageDirectory = Join-Path $RunDirectory 'storage'
	New-Item -ItemType Directory -Force -Path $storageDirectory | Out-Null
	$dbValue = $storageDirectory.Replace('\', '/')
	$logValue = $storageDirectory.Replace('\', '/')
	$config = (Get-Content -LiteralPath $templatePath -Raw) `
		-replace '(?m)^org\.vanilladb\.core\.storage\.file\.FileMgr\.DB_FILES_DIR=.*$',
			"org.vanilladb.core.storage.file.FileMgr.DB_FILES_DIR=$dbValue" `
		-replace '(?m)^org\.vanilladb\.core\.storage\.file\.FileMgr\.LOG_FILES_DIR=.*$',
			"org.vanilladb.core.storage.file.FileMgr.LOG_FILES_DIR=$logValue"
	$configPath = Join-Path $RunDirectory 'vanilladb.properties'
	$config | Set-Content -LiteralPath $configPath -Encoding utf8
	return $configPath
}

function Get-TestTotals {
	$totals = [ordered]@{ tests = 0; failures = 0; errors = 0; skipped = 0 }
	$reports = Get-ChildItem -LiteralPath $reportsPath -Filter 'TEST-*.xml' -ErrorAction SilentlyContinue
	foreach ($report in $reports) {
		[xml] $xml = Get-Content -LiteralPath $report.FullName -Raw
		$totals.tests += [int] $xml.testsuite.tests
		$totals.failures += [int] $xml.testsuite.failures
		$totals.errors += [int] $xml.testsuite.errors
		$totals.skipped += [int] $xml.testsuite.skipped
	}
	return $totals
}

New-Item -ItemType Directory -Force -Path $rawRoot | Out-Null
$previousJavaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Process')
$previousPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
$runResults = [System.Collections.Generic.List[object]]::new()

try {
	$env:JAVA_HOME = $jdk.Home
	$env:PATH = "$(Join-Path $jdk.Home 'bin');$previousPath"

	foreach ($campaign in $campaigns) {
		for ($repetition = 1; $repetition -le $Repetitions; $repetition++) {
			$runId = '{0}-{1:D2}' -f $campaign.id, $repetition
			$runDirectory = Join-Path $rawRoot $runId
			Reset-RunDirectory -RunDirectory $runDirectory
			$configPath = New-IsolatedConfig -RunDirectory $runDirectory
			$stdoutPath = Join-Path $runDirectory 'stdout.log'
			$stderrPath = Join-Path $runDirectory 'stderr.log'
			Remove-SurefireReports

			$arguments = @(
				'-Pmit-research',
				'--batch-mode',
				"-Dtest=$($campaign.selector)",
				'-DforkCount=1',
				'-DreuseForks=false',
				'-Dsurefire.rerunFailingTestsCount=0',
				"-Dorg.vanilladb.core.config.file=$configPath",
				'test'
			)
			$startedAt = Get-Date
			$process = Start-Process -FilePath $mavenCommand `
				-ArgumentList $arguments `
				-WorkingDirectory $repositoryRoot `
				-RedirectStandardOutput $stdoutPath `
				-RedirectStandardError $stderrPath `
				-NoNewWindow `
				-PassThru

			$completed = $process.WaitForExit($TimeoutSeconds * 1000)
			if (-not $completed) {
				& taskkill /PID $process.Id /T /F | Out-Null
				$process.WaitForExit()
			}

			$totals = Get-TestTotals
			$exitCode = if ($completed) { $process.ExitCode } else { -1 }
			$outcome = if (-not $completed) {
				'timeout'
			} elseif ($exitCode -eq 0 -and $totals.tests -eq $campaign.expectedTests -and
				$totals.failures -eq 0 -and $totals.errors -eq 0 -and $totals.skipped -eq 0) {
				'pass'
			} else {
				'fail'
			}

			$runResults.Add([pscustomobject][ordered]@{
				runId = $runId
				campaign = $campaign.id
				repetition = $repetition
				selector = $campaign.selector
				startedAt = $startedAt.ToString('o')
				durationSeconds = [Math]::Round(((Get-Date) - $startedAt).TotalSeconds, 3)
				processId = $process.Id
				exitCode = $exitCode
				outcome = $outcome
				tests = $totals.tests
				failures = $totals.failures
				errors = $totals.errors
				skipped = $totals.skipped
				configSha256 = (Get-FileHash -LiteralPath $configPath -Algorithm SHA256).Hash
				stdoutSha256 = (Get-FileHash -LiteralPath $stdoutPath -Algorithm SHA256).Hash
				stderrSha256 = (Get-FileHash -LiteralPath $stderrPath -Algorithm SHA256).Hash
			})

			Write-Host "[$runId] $outcome ($($totals.tests) tests, $([Math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1))s)"
		}
	}
} finally {
	if ($null -eq $previousJavaHome) {
		Remove-Item Env:JAVA_HOME -ErrorAction SilentlyContinue
	} else {
		$env:JAVA_HOME = $previousJavaHome
	}
	$env:PATH = $previousPath
}

$campaignResults = foreach ($campaign in $campaigns) {
	$runs = @($runResults | Where-Object campaign -eq $campaign.id)
	$durations = @($runs | ForEach-Object durationSeconds | Sort-Object)
	[ordered]@{
		id = $campaign.id
		selector = $campaign.selector
		repetitionsRequested = $Repetitions
		repetitionsCompleted = $runs.Count
		passes = @($runs | Where-Object outcome -eq 'pass').Count
		failures = @($runs | Where-Object outcome -ne 'pass').Count
		expectedTestsPerRun = $campaign.expectedTests
		durationSeconds = [ordered]@{
			min = $durations[0]
			median = $durations[[Math]::Floor($durations.Count / 2)]
			max = $durations[-1]
		}
	}
}

$summary = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	repositoryCommit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	jdk = $jdk
	mavenVersion = (& mvn -version 2>&1 | Select-Object -First 1)
	freshMavenProcesses = $runResults.Count
	forkCount = 1
	reuseForks = $false
	rerunFailingTestsCount = 0
	timeoutSeconds = $TimeoutSeconds
	isolatedStorageRootPerRun = $true
	campaigns = @($campaignResults)
}

$summaryDirectory = Split-Path -Parent $SummaryPath
New-Item -ItemType Directory -Force -Path $summaryDirectory | Out-Null
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryPath -Encoding utf8
$runResults | Export-Csv -LiteralPath $RunsPath -NoTypeInformation -Encoding utf8

$failedRuns = @($runResults | Where-Object outcome -ne 'pass')
if ($runResults.Count -ne ($campaigns.Count * $Repetitions) -or $failedRuns.Count -gt 0) {
	throw "Repetition gate failed: $($failedRuns.Count) non-passing runs."
}

Write-Host "Repetition evidence written to $SummaryPath and $RunsPath"

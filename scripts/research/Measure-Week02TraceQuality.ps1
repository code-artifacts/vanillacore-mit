[CmdletBinding()]
param(
	[int] $CompletenessRepetitions = 20,
	[int] $ProcessesPerMode = 3,
	[int] $SamplesPerProcess = 5,
	[int] $OperationsPerSample = 100000,
	[int] $WarmupOperations = 20000,
	[string] $OutputPath
)

Set-StrictMode -Version Latest

foreach ($value in @($CompletenessRepetitions, $ProcessesPerMode,
		$SamplesPerProcess, $OperationsPerSample)) {
	if ($value -le 0) {
		throw 'Repetition, process, sample, and operation counts must be positive.'
	}
}
$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-02\results\step-05-trace-quality.json'
}
$runId = "{0}-{1}" -f (Get-Date -Format 'yyyyMMdd-HHmmss'), $PID
$rawDirectory = Join-Path $repositoryRoot (
		"research\execution\week-02\raw\step-05\$runId")
$completenessDirectory = Join-Path $rawDirectory 'completeness'
$benchmarkDirectory = Join-Path $rawDirectory 'overhead'
New-Item -ItemType Directory -Force -Path $completenessDirectory,
	$benchmarkDirectory | Out-Null

& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode `
	"-Dvanillacore.mit.repetitions=$CompletenessRepetitions" `
	"-Dvanillacore.mit.traceDir=$completenessDirectory" `
	'-Dtest=LockTableReplayScenarioTest' test
if ($LASTEXITCODE -ne 0) {
	throw 'Completeness scenario run failed.'
}

$actualCounts = [ordered]@{}
foreach ($eventType in @('LOCK_CALL', 'WAIT_BEGIN', 'GRANT', 'RELEASE', 'TX_END')) {
	$actualCounts[$eventType] = 0
}
foreach ($traceFile in Get-ChildItem -LiteralPath $completenessDirectory -Filter '*.jsonl') {
	foreach ($line in Get-Content -LiteralPath $traceFile.FullName) {
		$event = $line | ConvertFrom-Json
		$actualCounts[$event.event_type]++
	}
}
$expectedPerRepetition = [ordered]@{
	LOCK_CALL = 10
	WAIT_BEGIN = 3
	GRANT = 9
	RELEASE = 9
	TX_END = 8
}
$eventMetrics = @()
$totalTruePositive = 0
$totalFalsePositive = 0
$totalFalseNegative = 0
foreach ($eventType in $expectedPerRepetition.Keys) {
	$expected = $expectedPerRepetition[$eventType] * $CompletenessRepetitions
	$actual = $actualCounts[$eventType]
	$truePositive = [Math]::Min($expected, $actual)
	$falsePositive = [Math]::Max(0, $actual - $expected)
	$falseNegative = [Math]::Max(0, $expected - $actual)
	$precision = if ($truePositive + $falsePositive -eq 0) {
		1.0
	} else {
		$truePositive / ($truePositive + $falsePositive)
	}
	$recall = if ($truePositive + $falseNegative -eq 0) {
		1.0
	} else {
		$truePositive / ($truePositive + $falseNegative)
	}
	$eventMetrics += [ordered]@{
		eventType = $eventType
		expected = $expected
		actual = $actual
		truePositive = $truePositive
		falsePositive = $falsePositive
		falseNegative = $falseNegative
		precision = [Math]::Round($precision, 6)
		recall = [Math]::Round($recall, 6)
	}
	$totalTruePositive += $truePositive
	$totalFalsePositive += $falsePositive
	$totalFalseNegative += $falseNegative
}

$benchmarkOrder = @()
for ($process = 1; $process -le $ProcessesPerMode; $process++) {
	if ($process % 2 -eq 1) {
		$benchmarkOrder += @('off', 'low')
	} else {
		$benchmarkOrder += @('low', 'off')
	}
}
$modeProcess = @{ off = 0; low = 0 }
foreach ($mode in $benchmarkOrder) {
	$modeProcess[$mode]++
	$output = Join-Path $benchmarkDirectory (
			"{0}-{1:D2}.csv" -f $mode, $modeProcess[$mode])
	& (Join-Path $PSScriptRoot 'Invoke-MavenJdk17.ps1') --batch-mode `
		"-Dvanillacore.mit.benchmarkMode=$mode" `
		"-Dvanillacore.mit.operations=$OperationsPerSample" `
		"-Dvanillacore.mit.samples=$SamplesPerProcess" `
		"-Dvanillacore.mit.warmupOperations=$WarmupOperations" `
		"-Dvanillacore.mit.benchmarkOutput=$output" `
		'-Dtest=LockTraceOverheadBenchmarkTest' test
	if ($LASTEXITCODE -ne 0) {
		throw "Overhead benchmark failed in $mode mode."
	}
}

function Get-Median {
	param([double[]] $Values)
	$sorted = @($Values | Sort-Object)
	$middle = [Math]::Floor($sorted.Count / 2)
	if ($sorted.Count % 2 -eq 1) {
		return $sorted[$middle]
	}
	return ($sorted[$middle - 1] + $sorted[$middle]) / 2.0
}

$modeResults = [ordered]@{}
foreach ($mode in @('off', 'low')) {
	$rows = @(Get-ChildItem -LiteralPath $benchmarkDirectory -Filter "$mode-*.csv" |
		ForEach-Object { Import-Csv -LiteralPath $_.FullName })
	$durations = @($rows | ForEach-Object { [double] $_.durationNanos })
	$operations = ($rows | Measure-Object -Property operations -Sum).Sum
	$dropped = ($rows | Measure-Object -Property dropped -Sum).Sum
	$polluted = @($rows | Where-Object {
		[int] $_.lockerMapSize -ne 0 -or
		[int] $_.lockByMapSize -ne 0 -or
		[int] $_.waitMapSize -ne 0
	}).Count
	$median = Get-Median -Values $durations
	$modeResults[$mode] = [ordered]@{
		processes = $ProcessesPerMode
		samples = $rows.Count
		measuredLockOperations = [long] $operations
		medianDurationNanos = [long] $median
		medianThroughputOpsPerSecond = [Math]::Round(
				$OperationsPerSample / ($median / 1000000000.0), 3)
		droppedEvents = [long] $dropped
		pollutedSamples = $polluted
	}
}
$overheadPercent = (
		$modeResults.low.medianDurationNanos /
		$modeResults.off.medianDurationNanos - 1.0) * 100.0
$microPrecision = $totalTruePositive / (
		$totalTruePositive + $totalFalsePositive)
$microRecall = $totalTruePositive / (
		$totalTruePositive + $totalFalseNegative)

$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	repositoryCommit = (& git -C $repositoryRoot rev-parse HEAD).Trim()
	traceSchemaVersion = 'vc-locktrace-0'
	completeness = [ordered]@{
		repetitionsPerScenario = $CompletenessRepetitions
		eventMetrics = $eventMetrics
		microPrecision = [Math]::Round($microPrecision, 6)
		microRecall = [Math]::Round($microRecall, 6)
		traceLoss = 0
		scope = 'event-type multiplicity for four deterministic direct scenarios'
	}
	overhead = [ordered]@{
		workload = 'single-thread S acquire/release over 100 resources'
		lowEventTypes = @('GRANT', 'RELEASE', 'TX_END')
		operationsPerSample = $OperationsPerSample
		samplesPerProcess = $SamplesPerProcess
		warmupOperationsPerProcess = $WarmupOperations
		modes = $modeResults
		lowOverheadPercent = [Math]::Round($overheadPercent, 3)
		targetPercent = 10
		hardCeilingPercent = 25
		withinTarget = ($overheadPercent -le 10)
		withinHardCeiling = ($overheadPercent -le 25)
	}
	baselineStress = [ordered]@{
		offModeLockOperations = $modeResults.off.measuredLockOperations
		unexplainedPollutedSamples = $modeResults.off.pollutedSamples
	}
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Host "Trace quality evidence written to $OutputPath"

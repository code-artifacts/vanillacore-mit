[CmdletBinding()]
param(
	[string] $UpstreamCommit = '03e1f2df49bb9664c8bdae11cf911f56b74bbc57',
	[string] $PatchPath,
	[string] $OutputPath
)

Set-StrictMode -Version Latest

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $PatchPath) {
	$PatchPath = Join-Path $repositoryRoot 'research\evidence\patches\pr-95-fix-locktable.patch'
}
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-01\results\step-02-baselines.json'
}

function Get-GitValue {
	param([string[]] $Arguments)
	$value = (& git -C $repositoryRoot @Arguments 2>&1 | Out-String).Trim()
	if ($LASTEXITCODE -ne 0) {
		throw "git $($Arguments -join ' ') failed: $value"
	}
	return $value
}

$repositoryCommit = Get-GitValue @('rev-parse', 'HEAD')
$repositoryTree = Get-GitValue @('rev-parse', 'HEAD^{tree}')
$repositorySourceTree = Get-GitValue @('rev-parse', 'HEAD:src')
$repositoryPomBlob = Get-GitValue @('rev-parse', 'HEAD:pom.xml')
$upstreamResolved = Get-GitValue @('rev-parse', $UpstreamCommit)
$upstreamTree = Get-GitValue @('rev-parse', "$UpstreamCommit`^{tree}")
$upstreamSourceTree = Get-GitValue @('rev-parse', "$UpstreamCommit`:src")
$upstreamPomBlob = Get-GitValue @('rev-parse', "$UpstreamCommit`:pom.xml")
$branch = Get-GitValue @('branch', '--show-current')
$remote = Get-GitValue @('remote', 'get-url', 'origin')

& git -C $repositoryRoot apply --check $PatchPath
$patchApplyExitCode = $LASTEXITCODE
$patchText = Get-Content -LiteralPath $PatchPath -Raw
$patchMailCommits = [regex]::Matches($patchText, '(?m)^From ([0-9a-f]{40}) ') |
	ForEach-Object { $_.Groups[1].Value }

$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	variants = [ordered]@{
		pristine = 'VC-HEAD-20230430'
		referenceFix = 'VC-REF-95'
	}
	repository = [ordered]@{
		commit = $repositoryCommit
		tree = $repositoryTree
		sourceTree = $repositorySourceTree
		pomBlob = $repositoryPomBlob
		branch = $branch
		origin = $remote
	}
	upstream = [ordered]@{
		commit = $upstreamResolved
		tree = $upstreamTree
		sourceTree = $upstreamSourceTree
		pomBlob = $upstreamPomBlob
		url = 'https://github.com/vanilladb/vanillacore'
	}
	patch = [ordered]@{
		path = 'research/evidence/patches/pr-95-fix-locktable.patch'
		sha256 = (Get-FileHash -LiteralPath $PatchPath -Algorithm SHA256).Hash
		gitBlob = (& git -C $repositoryRoot hash-object --no-filters $PatchPath).Trim()
		mailCommitIds = @($patchMailCommits)
		upstreamPullRequest = 'https://github.com/vanilladb/vanillacore/pull/95'
		applyCheck = ($patchApplyExitCode -eq 0)
	}
	checks = [ordered]@{
		repositorySourceMatchesUpstream = ($repositorySourceTree -eq $upstreamSourceTree)
		repositoryPomIntentionallyDiffers = ($repositoryPomBlob -ne $upstreamPomBlob)
	}
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8

if (-not $result.patch.applyCheck) {
	throw 'PR #95 patch does not apply to the current source baseline.'
}
if (-not $result.checks.repositorySourceMatchesUpstream) {
	throw 'Current src tree differs from the pinned upstream baseline.'
}

Write-Host "Baseline identity written to $OutputPath"

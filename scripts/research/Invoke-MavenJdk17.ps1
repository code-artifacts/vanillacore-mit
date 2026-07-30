[CmdletBinding()]
param(
	[Parameter(Position = 0, ValueFromRemainingArguments)]
	[string[]] $MavenArguments = @('--batch-mode', 'verify')
)

Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'common\JavaToolchain.ps1')

$jdk = Resolve-ResearchJavaHome -Major 17
if ($jdk.Vendor -ne 'Eclipse Adoptium') {
	throw "Expected Eclipse Adoptium, found '$($jdk.Vendor)'."
}
if ($jdk.RuntimeVersion -ne '17.0.20+8') {
	throw "Expected Temurin runtime 17.0.20+8, found '$($jdk.RuntimeVersion)'."
}

$previousJavaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Process')
$previousPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
$researchArguments = @('-Pmit-research') + $MavenArguments

try {
	$env:JAVA_HOME = $jdk.Home
	$env:PATH = "$(Join-Path $jdk.Home 'bin');$previousPath"
	Write-Host "Using $($jdk.Vendor) JDK $($jdk.RuntimeVersion) at $($jdk.Home)"
	& mvn @researchArguments
	$exitCode = $LASTEXITCODE
} finally {
	if ($null -eq $previousJavaHome) {
		Remove-Item Env:JAVA_HOME -ErrorAction SilentlyContinue
	} else {
		$env:JAVA_HOME = $previousJavaHome
	}
	$env:PATH = $previousPath
}

if ($exitCode -ne 0) {
	throw "Maven exited with code $exitCode."
}

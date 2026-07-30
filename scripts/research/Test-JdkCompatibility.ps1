[CmdletBinding()]
param(
	[string] $OutputPath
)

Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'common\JavaToolchain.ps1')

$repositoryRoot = (& git -C $PSScriptRoot rev-parse --show-toplevel).Trim()
if (-not $OutputPath) {
	$OutputPath = Join-Path $repositoryRoot 'research\execution\week-01\results\step-01-environment.json'
}

$jdk17 = Resolve-ResearchJavaHome -Major 17
$jdk25 = Resolve-ResearchJavaHome -Major 25
$jnaJar = Join-Path $HOME '.m2\repository\net\java\dev\jna\jna\4.0.0\jna-4.0.0.jar'
if (-not (Test-Path -LiteralPath $jnaJar)) {
	throw "JNA 4.0.0 is not present at '$jnaJar'. Resolve project dependencies with JDK 17 first."
}

$jdk17JarOutput = (& (Join-Path $jdk17.Home 'bin\jar.exe') tf $jnaJar 2>&1 | Out-String)
$jdk17JarExitCode = $LASTEXITCODE
$jdk25JarOutput = (& (Join-Path $jdk25.Home 'bin\jar.exe') tf $jnaJar 2>&1 | Out-String)
$jdk25JarExitCode = $LASTEXITCODE

$previousJavaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Process')
$previousPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
try {
	$env:JAVA_HOME = $jdk25.Home
	$env:PATH = "$(Join-Path $jdk25.Home 'bin');$previousPath"
	$mavenOutput = (& mvn -Pmit-research --batch-mode '-Denforcer.skip=true' '-DskipTests' clean compile 2>&1 | Out-String)
	$mavenExitCode = $LASTEXITCODE
} finally {
	if ($null -eq $previousJavaHome) {
		Remove-Item Env:JAVA_HOME -ErrorAction SilentlyContinue
	} else {
		$env:JAVA_HOME = $previousJavaHome
	}
	$env:PATH = $previousPath
}

$errorPattern = 'Invalid CEN header \(invalid zip64 extra data field size\)'
$result = [ordered]@{
	schemaVersion = 1
	recordedAt = (Get-Date).ToString('o')
	host = [ordered]@{
		os = [System.Environment]::OSVersion.VersionString
		architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
	}
	jdk17 = $jdk17
	jdk25 = $jdk25
	jna = [ordered]@{
		coordinate = 'net.java.dev.jna:jna:4.0.0'
		path = $jnaJar
		sha256 = (Get-FileHash -LiteralPath $jnaJar -Algorithm SHA256).Hash
	}
	probes = [ordered]@{
		jdk17JarReadable = ($jdk17JarExitCode -eq 0)
		jdk25JarReadable = ($jdk25JarExitCode -eq 0)
		jdk25JarError = ($jdk25JarOutput.Trim() -split "`r?`n" | Select-Object -First 1)
		jdk25MavenExitCode = $mavenExitCode
		jdk25MavenMatchedZip64Error = ($mavenOutput -match $errorPattern)
	}
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8

if (-not $result.probes.jdk17JarReadable) {
	throw 'JDK 17 unexpectedly rejected JNA 4.0.0.'
}
if ($result.probes.jdk25JarReadable -or -not $result.probes.jdk25MavenMatchedZip64Error) {
	throw 'JDK 25 compatibility probe did not reproduce the expected Zip64 failure.'
}

Write-Host "Compatibility evidence written to $OutputPath"

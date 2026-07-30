Set-StrictMode -Version Latest

function Get-ResearchJavaInfo {
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[string] $JavaHome
	)

	$java = Join-Path $JavaHome 'bin\java.exe'
	if (-not (Test-Path -LiteralPath $java)) {
		throw "Java executable not found under '$JavaHome'."
	}

	$settings = (& $java -XshowSettings:properties -version 2>&1 | Out-String)
	$major = [regex]::Match($settings, '(?m)^\s*java\.specification\.version\s*=\s*(\d+)\s*$')
	$vendor = [regex]::Match($settings, '(?m)^\s*java\.vendor\s*=\s*(.+?)\s*$')
	$version = [regex]::Match($settings, '(?m)^\s*java\.version\s*=\s*(.+?)\s*$')
	$runtimeVersion = [regex]::Match($settings, '(?m)^\s*java\.runtime\.version\s*=\s*(.+?)\s*$')

	if (-not ($major.Success -and $vendor.Success -and $version.Success -and $runtimeVersion.Success)) {
		throw "Unable to read Java properties from '$JavaHome'."
	}

	[pscustomobject]@{
		Home = (Resolve-Path -LiteralPath $JavaHome).Path
		Major = [int] $major.Groups[1].Value
		Vendor = $vendor.Groups[1].Value
		Version = $version.Groups[1].Value
		RuntimeVersion = $runtimeVersion.Groups[1].Value
	}
}

function Resolve-ResearchJavaHome {
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateSet(17, 25)]
		[int] $Major
	)

	$candidates = [System.Collections.Generic.List[string]]::new()
	foreach ($name in @("VANILLADB_JDK${Major}_HOME", "JAVA${Major}_HOME")) {
		$value = [Environment]::GetEnvironmentVariable($name, 'Process')
		if ($value) {
			$candidates.Add($value)
		}
	}

	$registryPath = "HKLM:\SOFTWARE\JavaSoft\JDK\$Major"
	if (Test-Path -LiteralPath $registryPath) {
		$javaHome = (Get-ItemProperty -LiteralPath $registryPath).JavaHome
		if ($javaHome) {
			$candidates.Add($javaHome)
		}
	}

	$patterns = if ($Major -eq 17) {
		@('C:\Program Files\Eclipse Adoptium\jdk-17*')
	} else {
		@('C:\Program Files\Java\jdk-25*')
	}

	foreach ($pattern in $patterns) {
		Get-Item -Path $pattern -ErrorAction SilentlyContinue |
			ForEach-Object { $candidates.Add($_.FullName) }
	}

	foreach ($candidate in $candidates | Select-Object -Unique) {
		if (-not (Test-Path -LiteralPath $candidate)) {
			continue
		}
		$info = Get-ResearchJavaInfo -JavaHome $candidate
		if ($info.Major -eq $Major) {
			return $info
		}
	}

	throw "No JDK $Major installation found. Set VANILLADB_JDK${Major}_HOME."
}

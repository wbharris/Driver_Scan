# Collect PnP devices, signed drivers, optional Windows Update driver offers.
# Output: one JSON object on stdout. Scan only — does not install.
# Does not require Administrator. CIM/WU failures are recorded on the payload.
[CmdletBinding()]
param(
    [switch]$IncludeWindowsUpdate
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

function Convert-CimDate {
    param($Value)
    if ($null -eq $Value -or $Value -eq "") { return $null }
    try { return ([datetime]$Value).ToString("s") } catch { return [string]$Value }
}

function Get-Devices {
    $err = $null
    $items = @()
    try {
        $entities = @(Get-CimInstance -ClassName Win32_PnPEntity -ErrorAction Stop)
        foreach ($e in $entities) {
            if ($null -eq $e) { continue }
            if ($null -ne $e.Present -and [bool]$e.Present -eq $false) { continue }
            $code = 0
            try { $code = [int]$e.ConfigManagerErrorCode } catch { $code = 0 }
            $items += [pscustomobject]@{
                name                   = $e.Name
                manufacturer           = $e.Manufacturer
                status                 = [string]$e.Status
                class                  = $e.PNPClass
                instanceId             = $e.PNPDeviceID
                deviceId               = $e.DeviceID
                configManagerErrorCode = $code
                problem                = [string]$e.StatusInfo
                present                = $e.Present
            }
        }
    } catch {
        $err = $_.Exception.Message
    }
    return [pscustomobject]@{ Items = @($items); Error = $err }
}

function Get-SignedDrivers {
    $err = $null
    $items = @()
    try {
        $rows = @(Get-CimInstance -ClassName Win32_PnPSignedDriver -ErrorAction Stop)
        foreach ($d in $rows) {
            if ($null -eq $d) { continue }
            $items += [pscustomobject]@{
                deviceName    = $d.DeviceName
                deviceId      = $d.DeviceID
                driverVersion = $d.DriverVersion
                driverDate    = Convert-CimDate $d.DriverDate
                manufacturer  = $d.Manufacturer
                infName       = $d.InfName
            }
        }
    } catch {
        $err = $_.Exception.Message
    }
    return [pscustomobject]@{ Items = @($items); Error = $err }
}

function Get-WuDrivers {
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $result = $searcher.Search("IsInstalled=0 and Type='Driver'")
    $items = New-Object System.Collections.Generic.List[object]
    if ($result -and $result.Updates) {
        foreach ($u in $result.Updates) {
            $items.Add([pscustomobject]@{
                title       = $u.Title
                description = $u.Description
            }) | Out-Null
        }
    }
    return @($items.ToArray())
}

$collectErrors = New-Object System.Collections.Generic.List[string]
$cs = $null
$bios = $null
$os = $null
try { $cs = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop } catch { $collectErrors.Add("Win32_ComputerSystem: $($_.Exception.Message)") | Out-Null }
try { $bios = Get-CimInstance -ClassName Win32_BIOS -ErrorAction Stop } catch { $collectErrors.Add("Win32_BIOS: $($_.Exception.Message)") | Out-Null }
try { $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop } catch { $collectErrors.Add("Win32_OperatingSystem: $($_.Exception.Message)") | Out-Null }

$devResult = Get-Devices
$devices = @($devResult.Items)
if ($devResult.Error) { [void]$collectErrors.Add("Win32_PnPEntity: $($devResult.Error)") }

$sigResult = Get-SignedDrivers
$signed = @($sigResult.Items)
if ($sigResult.Error) { [void]$collectErrors.Add("Win32_PnPSignedDriver: $($sigResult.Error)") }

$payload = [ordered]@{
    hostname             = $env:COMPUTERNAME
    os                   = if ($os) { $os.Caption } else { $null }
    kernel               = [Environment]::OSVersion.Version.ToString()
    manufacturer         = if ($cs) { $cs.Manufacturer } else { $null }
    model                = if ($cs) { $cs.Model } else { $null }
    serial               = if ($bios) { $bios.SerialNumber } else { $null }
    devices              = @($devices)
    signedDrivers        = @($signed)
    windowsUpdateDrivers = @()
    windowsUpdateError   = $null
    collectErrors        = @($collectErrors.ToArray())
}

if ($IncludeWindowsUpdate) {
    try {
        $payload.windowsUpdateDrivers = @(Get-WuDrivers)
    }
    catch {
        $payload.windowsUpdateError = $_.Exception.Message
    }
}

$payload | ConvertTo-Json -Depth 6 -Compress

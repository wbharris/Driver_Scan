# Collect PnP devices, signed drivers, optional Windows Update driver offers.
# Output: one JSON object on stdout. Scan only — does not install.
[CmdletBinding()]
param(
    [switch]$IncludeWindowsUpdate
)

$ErrorActionPreference = "SilentlyContinue"

function Get-Devices {
    $entities = Get-CimInstance -ClassName Win32_PnPEntity
    foreach ($e in $entities) {
        if ($null -eq $e) { continue }
        [pscustomobject]@{
            name                    = $e.Name
            manufacturer            = $e.Manufacturer
            status                  = [string]$e.Status
            class                   = $e.PNPClass
            instanceId              = $e.PNPDeviceID
            deviceId                = $e.DeviceID
            configManagerErrorCode  = [int]$e.ConfigManagerErrorCode
            problem                 = $e.StatusInfo
            present                 = $e.Present
        }
    }
}

function Get-SignedDrivers {
    $rows = Get-CimInstance -ClassName Win32_PnPSignedDriver
    foreach ($d in $rows) {
        if ($null -eq $d) { continue }
        [pscustomobject]@{
            deviceName    = $d.DeviceName
            deviceId      = $d.DeviceID
            driverVersion = $d.DriverVersion
            driverDate    = if ($d.DriverDate) { $d.DriverDate.ToString("s") } else { $null }
            manufacturer  = $d.Manufacturer
            infName       = $d.InfName
        }
    }
}

function Get-WuDrivers {
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    $result = $searcher.Search("IsInstalled=0 and Type='Driver'")
    $items = @()
    if ($result -and $result.Updates) {
        foreach ($u in $result.Updates) {
            $items += [pscustomobject]@{
                title       = $u.Title
                description = $u.Description
            }
        }
    }
    return $items
}

$payload = [ordered]@{
    hostname             = $env:COMPUTERNAME
    devices              = @(Get-Devices)
    signedDrivers        = @(Get-SignedDrivers)
    windowsUpdateDrivers = @()
    windowsUpdateError   = $null
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

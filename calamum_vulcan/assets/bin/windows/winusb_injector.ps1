[CmdletBinding()]
param(
  [string]$VendorId = '0x04E8',
  [string]$ProductId = '0x685D',
  [string]$Reason = 'Calamum Vulcan native USB remediation'
)

$ErrorActionPreference = 'Stop'

function Normalize-HexId {
  param([string]$Value)
  $normalized = ($Value ?? '').Trim()
  if ($normalized.StartsWith('0x', [System.StringComparison]::OrdinalIgnoreCase)) {
    $normalized = $normalized.Substring(2)
  }
  return $normalized.ToUpperInvariant().PadLeft(4, '0')
}

$vendor = Normalize-HexId -Value $VendorId
$product = Normalize-HexId -Value $ProductId
$hardwareId = 'USB\\VID_{0}&PID_{1}' -f $vendor, $product
$tempRoot = Join-Path $env:TEMP ('calamum_vulcan_winusb_{0}_{1}' -f $vendor, $product)
$infPath = Join-Path $tempRoot 'calamum_vulcan_winusb.inf'
$driverStamp = Get-Date -Format 'MM/dd/yyyy,1.0.0.0'

New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

$existingWinUsb = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
  Where-Object {
    $_.InstanceId -like ('USB\\VID_{0}&PID_{1}*' -f $vendor, $product)
  } |
  Where-Object {
    ($_.Service -eq 'WinUSB') -or ($_.Class -eq 'USBDevice')
  } |
  Select-Object -First 1

if ($null -ne $existingWinUsb) {
  Write-Output ('[USB-REMEDIATION] status=already_bound hardware_id={0} instance_id="{1}" reason="{2}"' -f $hardwareId, $existingWinUsb.InstanceId, $Reason)
  exit 0
}

$infContent = @"
[Version]
Signature="$Windows NT$"
Class=USBDevice
ClassGuid={88BAE032-5A81-49f0-BC3D-A4FF138216D6}
Provider=%ProviderName%
DriverVer=$driverStamp

[Manufacturer]
%ProviderName%=Calamum,NTamd64

[Calamum.NTamd64]
%DeviceName%=USB_Install,$hardwareId

[USB_Install]
Include=winusb.inf
Needs=WINUSB.NT

[USB_Install.Services]
Include=winusb.inf
Needs=WINUSB.NT.Services

[USB_Install.HW]
AddReg=DeviceInterfaceGuid_AddReg

[DeviceInterfaceGuid_AddReg]
HKR,,DeviceInterfaceGUIDs,0x10000,"{F4F0B1A2-0D54-4C35-8BE2-F4F7D8A7D9A1}"

[Strings]
ProviderName="Calamum Vulcan"
DeviceName="Samsung Download Mode (Calamum Native USB)"
"@

Set-Content -Path $infPath -Value $infContent -Encoding ASCII
Write-Output ('[USB-REMEDIATION] status=install_attempt hardware_id={0} inf="{1}" reason="{2}"' -f $hardwareId, $infPath, $Reason)

try {
  $pnputil = Join-Path $env:WINDIR 'System32\pnputil.exe'
  & $pnputil /add-driver $infPath /install
  & $pnputil /scan-devices
  Write-Output ('[USB-REMEDIATION] status=install_complete hardware_id={0}' -f $hardwareId)
  exit 0
}
catch {
  Write-Error ('[USB-REMEDIATION] status=install_failed hardware_id={0} detail="{1}"' -f $hardwareId, $_.Exception.Message)
  exit 1
}

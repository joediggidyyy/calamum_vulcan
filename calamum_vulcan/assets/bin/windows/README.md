# Windows USB Assets

This directory contains standalone assets required for CodeSentinel zero-touch packaging rules.

## Bundled payloads

- `libusb-1.0.dll`: Official upstream `libusb` Windows runtime bundled from
	`https://github.com/libusb/libusb/releases/tag/v1.0.29`
	using the `libusb-1.0.29.7z` asset and the `VS2022/MS64/dll/libusb-1.0.dll`
	payload.
- `LIBUSB-COPYING.txt`: Upstream LGPL-2.1 license text shipped beside the DLL.
- `winusb_injector.ps1`: Best-effort WinUSB remediation helper launched when
	native USB access needs platform repair.

## Notes

- Current bundled DLL SHA-256:
	`5072054CB3002AE071F382AD5C2C2B0092D9451C537D0C13444C2B6F968F7251`
- The remediation helper attempts a WinUSB binding flow through `pnputil` and a
	generated INF that targets the Samsung download-mode hardware id.
- If a future toolchain requires a different libusb build, replace the DLL with
	another official upstream payload and update this README plus the bundled
	license text.

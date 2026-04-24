# Windows USB Assets

This directory contains standalone assets required for CodeSentinel zero-touch packaging rules.

## Bundled payloads

- `libusb-1.0.dll`: Official upstream `libusb` Windows runtime bundled from
	`https://github.com/libusb/libusb/releases/tag/v1.0.29`
	using the `libusb-1.0.29.7z` asset and the `VS2022/MS64/dll/libusb-1.0.dll`
	payload. This is the 64-bit backend used by the repo-owned native USB scan
	path.
- `LIBUSB-COPYING.txt`: Upstream LGPL-2.1 license text shipped beside the DLL.
- `winusb_injector.ps1`: Best-effort WinUSB remediation helper launched when
	native USB access needs platform repair.
- `heimdall/heimdall.exe`: Official upstream Heimdall command-line runtime
	bundled from `https://bitbucket.org/benjamin_dobell/heimdall/downloads/heimdall-suite-1.4.0-win32.zip`
	so the supported-path integrated runtime no longer depends on an operator-
	managed Heimdall installation.
- `heimdall/libusb-1.0.dll`: The matching 32-bit upstream `libusb` companion
	shipped beside the bundled Heimdall executable to avoid conflicting with the
	64-bit native USB backend DLL at this directory root.
- `heimdall/LICENSE.txt`: Upstream Heimdall MIT license text shipped beside the
	bundled runtime payload.
- `heimdall/README.md`: Provenance and runtime notes for the bundled Heimdall
	CLI payload.

## Notes

- Current bundled DLL SHA-256:
	`5072054CB3002AE071F382AD5C2C2B0092D9451C537D0C13444C2B6F968F7251`
- The remediation helper attempts a WinUSB binding flow through `pnputil` and a
	generated INF that targets the Samsung download-mode hardware id.
- The packaged Heimdall payload is isolated under `heimdall/` because it is a
	32-bit CLI bundle with its own `libusb-1.0.dll`; keeping it out of the root
	avoids colliding with the 64-bit `pyusb` backend DLL used by native USB
	detection.
- On Windows hosts where the bundled Heimdall executable returns exit code
	`0xC0000135`, the missing dependency is typically the Microsoft Visual C++
	2012 x86 runtime rather than the Calamum-owned payload itself.
- If a future toolchain requires a different libusb build, replace the DLL with
	another official upstream payload and update this README plus the bundled
	license text.

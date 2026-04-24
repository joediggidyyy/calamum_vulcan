# Bundled Heimdall Windows Runtime

This directory carries the Calamum-owned packaged Heimdall command-line payload used by the Windows supported-path runtime lane.

## Provenance

- upstream project: `Benjamin-Dobell/Heimdall`
- upstream bundle: `https://bitbucket.org/benjamin_dobell/heimdall/downloads/heimdall-suite-1.4.0-win32.zip`
- bundled executable: `heimdall.exe`
- bundled companion DLL: `libusb-1.0.dll`
- bundled executable SHA-256: `4AC8E52846354465563F6657C4ED35F9078796C786EA9FE33F631AD5F92AA412`
- bundled companion DLL SHA-256: `9D9688B6B4C2AD6A04F1916EF6FD26D64297123EBDE330615E0CB370A715B76E`

## Packaging notes

- This payload is intentionally isolated under `assets/bin/windows/heimdall/` so its 32-bit `libusb-1.0.dll` does not collide with the 64-bit root-level `libusb-1.0.dll` used by the repo-owned native USB scan path.
- Runtime resolution in `calamum_vulcan/adapters/heimdall/runtime.py` now prefers this packaged executable before falling back to PATH or common Windows install locations.
- If the packaged runtime exits with Windows code `0xC0000135`, the current workstation is usually missing the Microsoft Visual C++ 2012 x86 runtime or another required companion DLL.
- The bundled payload remains lower-transport implementation detail; operator-visible supported-path control surfaces should continue to narrate `integrated-runtime`, not external Heimdall.

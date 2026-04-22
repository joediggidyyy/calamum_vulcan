# Windows USB Assets

This directory contains standalone assets required for CodeSentinel zero-touch packaging rules.

## Requirements
- `libusb-1.0.dll`: Required backend for `pyusb` wrapper to function on Windows.
- `libusb_injector.bat` or `elevation_helper.exe`: Automated driver injection payload for WinUSB/libusbK on unsupported devices.

*Note: Binaries will be sourced and cached separately from git.*

# Linux USB Assets

This directory contains standalone assets required for CodeSentinel zero-touch packaging rules.

## Bundled payloads

- `udev_injector.sh`: Automated udev rules deployment helper. When launched with
	`pkexec` or `sudo`, it installs
	`/etc/udev/rules.d/70-calamum-vulcan-samsung-download.rules`, reloads udev,
	and triggers the Samsung download-mode match.

## Notes

- The helper defaults to the Samsung download-mode hardware ids `04e8:685d` and
	also accepts `--vendor-id` / `--product-id` overrides.
- Linux generally expects the platform `libusb` runtime to be available already;
	this directory focuses on USB-access remediation rather than bundling a second
	shared library copy.

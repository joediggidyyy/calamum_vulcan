"""Native USB detection and remediation helpers for Sprint 0.5.0."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
import importlib
import logging
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable
from typing import Optional
from typing import Sequence
from typing import Tuple

from ..runtime_dependencies import attempt_runtime_dependency_repair

try:
    import usb.backend.libusb1 as _usb_backend_libusb1
    import usb.core as _usb_core
    import usb.util as _usb_util
except ImportError:
    _usb_backend_libusb1 = None
    _usb_core = None
    _usb_util = None


SAMSUNG_VENDOR_ID = 0x04E8
SAMSUNG_DOWNLOAD_MODE_PRODUCT_IDS = {
    0x685D: 'Samsung download mode',
}
PRODUCT_CODE_PATTERN = re.compile(r'\bSM[-_][A-Z0-9]+\b', re.IGNORECASE)
APP_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_ASSET_ROOT = APP_ROOT / 'assets' / 'bin' / 'windows'
LINUX_ASSET_ROOT = APP_ROOT / 'assets' / 'bin' / 'linux'
WINDOWS_BACKEND_DLL = WINDOWS_ASSET_ROOT / 'libusb-1.0.dll'
WINDOWS_INJECTOR_SCRIPT = WINDOWS_ASSET_ROOT / 'winusb_injector.ps1'
LINUX_INJECTOR_SCRIPT = LINUX_ASSET_ROOT / 'udev_injector.sh'
PYUSB_AVAILABLE = False


def _import_pyusb_modules() -> Tuple[object, object, object, Optional[str]]:
    """Import the pyusb modules and return them with one optional error note."""

    try:
        backend_module = importlib.import_module('usb.backend.libusb1')
        usb_core_module = importlib.import_module('usb.core')
        usb_util_module = importlib.import_module('usb.util')
    except ImportError as error:
        return None, None, None, str(error)
    return backend_module, usb_core_module, usb_util_module, None


def _refresh_pyusb_availability() -> None:
    """Refresh the public pyusb-availability flag after imports change."""

    global PYUSB_AVAILABLE
    PYUSB_AVAILABLE = (
        _usb_core is not None
        and _usb_util is not None
        and _usb_backend_libusb1 is not None
    )
    usb_package = sys.modules.get('calamum_vulcan.usb')
    if usb_package is not None:
        setattr(usb_package, 'PYUSB_AVAILABLE', PYUSB_AVAILABLE)


def _set_pyusb_modules(
    backend_module: object,
    usb_core_module: object,
    usb_util_module: object,
) -> None:
    """Persist the process-wide pyusb module references."""

    global _usb_backend_libusb1
    global _usb_core
    global _usb_util
    _usb_backend_libusb1 = backend_module
    _usb_core = usb_core_module
    _usb_util = usb_util_module
    _refresh_pyusb_availability()


_set_pyusb_modules(_usb_backend_libusb1, _usb_core, _usb_util)


@dataclass(frozen=True)
class USBDeviceDescriptor:
    """One normalized native USB download-mode device descriptor."""

    vendor_id: int
    product_id: int
    bus: Optional[int]
    address: Optional[int]
    serial_number: str
    manufacturer: Optional[str] = None
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    command_ready: bool = True


@dataclass(frozen=True)
class USBProbeResult:
    """Result surface returned by the native USB detection seam."""

    state: str
    summary: str
    devices: Tuple[USBDeviceDescriptor, ...] = ()
    notes: Tuple[str, ...] = ()
    remediation_command: Optional[str] = None


@dataclass(frozen=True)
class _NormalizedUSBDevice:
    """Internal normalized USB result with supplementary descriptor notes."""

    descriptor: USBDeviceDescriptor
    notes: Tuple[str, ...] = ()


def _normalize_text(value: object) -> Optional[str]:
    """Return one trimmed text value or ``None`` when it is blank."""

    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


class VulcanUSBScanner:
    """Repo-owned native USB detector for Samsung download mode."""

    def __init__(
        self,
        backend_path: Optional[Path] = None,
        usb_core_module=None,
        usb_util_module=None,
        backend_factory: Optional[Callable[[Optional[str]], object]] = None,
        elevation_runner: Optional[Callable[[Sequence[str]], object]] = None,
        platform_name: Optional[str] = None,
    ) -> None:
        self.logger = logging.getLogger('vulcan.usb')
        self._usb_core = usb_core_module if usb_core_module is not None else _usb_core
        self._usb_util = usb_util_module if usb_util_module is not None else _usb_util
        self._backend_factory = backend_factory or self._default_backend_factory
        self._elevation_runner = elevation_runner or self._default_elevation_runner
        self._platform_name = platform_name or sys.platform
        self.backend = None
        self.backend_path = None  # type: Optional[Path]
        self._configured_backend_path = backend_path
        self._backend_note = 'Native USB backend has not been initialized yet.'
        self._init_backend(backend_path)

    def probe_download_mode_devices(
        self,
        read_identity_strings: bool = True,
    ) -> USBProbeResult:
        """Detect Samsung download-mode devices through the native USB seam."""

        repair_note = None  # type: Optional[str]
        if self._usb_core is None or self._usb_util is None:
            repair_note = self._repair_runtime_dependencies()
        if self._usb_core is None or self._usb_util is None:
            return USBProbeResult(
                state='failed',
                summary=(
                    'Native USB detection is unavailable because the Calamum '
                    'Vulcan runtime dependency set is still incomplete after '
                    'automatic repair.'
                ),
                notes=tuple(
                    note
                    for note in (
                        'Packaging/runtime issue: required USB runtime modules are '
                        'not importable.',
                        repair_note,
                    )
                    if note is not None
                ),
            )

        if self._platform_name.startswith('win') and self.backend is None:
            remediation_command = self.trigger_elevation_helper(
                'Bundled libusb backend is unavailable on Windows.',
            )
            notes = [
                'Bundled libusb backend could not be resolved on Windows.',
            ]
            if repair_note is not None:
                notes.insert(0, repair_note)
            if remediation_command is not None:
                notes.append(
                    'USB remediation helper launched: {command}'.format(
                        command=remediation_command,
                    )
                )
            return USBProbeResult(
                state='failed',
                summary=(
                    'Native USB detection could not start because the bundled libusb '
                    'backend is not currently available on Windows.'
                ),
                notes=tuple(notes),
                remediation_command=remediation_command,
            )

        try:
            devices = tuple(
                self._usb_core.find(
                    find_all=True,
                    backend=self.backend,
                    idVendor=SAMSUNG_VENDOR_ID,
                    custom_match=self._matches_supported_download_mode_device,
                )
                or ()
            )
        except Exception as error:
            remediation_command = None
            notes = [
                self._backend_note,
                'USB probe error: {error}'.format(error=error),
            ]
            if repair_note is not None:
                notes.insert(0, repair_note)
            if self._requires_platform_remediation(error):
                remediation_command = self.trigger_elevation_helper(str(error))
                if remediation_command is not None:
                    notes.append(
                        'USB remediation helper launched: {command}'.format(
                            command=remediation_command,
                        )
                    )
                return USBProbeResult(
                    state='failed',
                    summary=(
                        'Native USB detection could not access the Samsung download-mode '
                        'lane until platform USB remediation completes.'
                    ),
                    notes=tuple(notes),
                    remediation_command=remediation_command,
                )
            return USBProbeResult(
                state='failed',
                summary=(
                    'Native USB detection failed before a trustworthy Samsung '
                    'download-mode identity could be built.'
                ),
                notes=tuple(notes),
            )

        normalized_results_list = []  # type: list[_NormalizedUSBDevice]
        for device in devices:
            try:
                normalized_results_list.append(
                    self._normalize_device(
                        device,
                        read_identity_strings=read_identity_strings,
                    )
                )
            finally:
                if self._usb_util is not None and hasattr(self._usb_util, 'dispose_resources'):
                    try:
                        self._usb_util.dispose_resources(device)
                    except Exception:
                        self.logger.debug(
                            'Native USB resource disposal raised after probe normalization.',
                            exc_info=True,
                        )
        normalized_results = tuple(normalized_results_list)
        normalized_devices = tuple(
            result.descriptor for result in normalized_results
        )
        if not normalized_devices:
            return USBProbeResult(
                state='cleared',
                summary='Native USB scan did not detect a Samsung download-mode device.',
                notes=tuple(
                    note
                    for note in (repair_note, self._backend_note)
                    if note is not None
                ),
            )

        summary = (
            'Native USB scan detected a Samsung download-mode device.'
            if len(normalized_devices) == 1
            else 'Native USB scan detected Samsung download-mode devices.'
        )
        state = 'detected'

        notes = [self._backend_note]
        if repair_note is not None:
            notes.insert(0, repair_note)
        for result in normalized_results:
            notes.extend(result.notes)
        if any(device.product_code is None for device in normalized_devices):
            notes.append(
                'USB descriptors did not expose a Samsung product code for every '
                'detected device; continue with bounded download-mode presence and use Read PIT to gather stronger device truth.'
            )
        return USBProbeResult(
            state=state,
            summary=summary,
            devices=normalized_devices,
            notes=tuple(notes),
        )

    def get_samsung_devices(self) -> Tuple[USBDeviceDescriptor, ...]:
        """Return normalized Samsung download-mode devices for compatibility callers."""

        return self.probe_download_mode_devices().devices

    def _repair_runtime_dependencies(self) -> Optional[str]:
        """Attempt one bounded repair of the declared runtime dependency set."""

        note = attempt_runtime_dependency_repair(self.logger)
        backend_module, usb_core_module, usb_util_module, import_error = _import_pyusb_modules()
        if usb_core_module is None or usb_util_module is None:
            if note is not None:
                return note
            return (
                'Automatic runtime dependency repair did not restore the '
                'required USB runtime modules: {error}'.format(
                    error=(import_error or 'unknown import failure'),
                )
            )
        _set_pyusb_modules(backend_module, usb_core_module, usb_util_module)
        self._usb_core = usb_core_module
        self._usb_util = usb_util_module
        self._init_backend(self._configured_backend_path)
        return note

    def trigger_elevation_helper(self, reason: Optional[str] = None) -> Optional[str]:
        """Launch the packaged OS helper used to remediate USB access issues."""

        command = self._elevation_command(reason)
        if command is None:
            self.logger.warning(
                'Native USB remediation was requested, but no packaged helper is available.'
            )
            return None
        try:
            self._elevation_runner(command)
        except Exception as error:  # pragma: no cover - defensive runtime guardrail
            self.logger.warning(
                'Failed to launch USB remediation helper: %s',
                error,
            )
            return None
        return self._display_command(command)

    def _init_backend(self, backend_path: Optional[Path]) -> None:
        """Load the bundled Windows libusb backend when required."""

        if self._usb_core is None or self._backend_factory is None:
            self._backend_note = (
                'Native USB backend unavailable because required USB runtime '
                'modules are not importable.'
            )
            return

        if not self._platform_name.startswith('win'):
            try:
                self.backend = self._backend_factory(None)
            except Exception as error:
                self.backend = None
                self._backend_note = 'Native USB backend resolution failed: {error}'.format(
                    error=error,
                )
                return
            self._backend_note = 'Native USB backend resolved through the platform libusb loader.'
            return

        for candidate in self._candidate_backend_paths(backend_path):
            try:
                backend = self._backend_factory(str(candidate))
            except Exception as error:
                self.logger.warning(
                    'Bundled libusb candidate failed to load from %s: %s',
                    candidate,
                    error,
                )
                continue
            if backend is None:
                continue
            self.backend = backend
            self.backend_path = candidate
            self._backend_note = 'Native USB backend resolved from bundled libusb: {path}'.format(
                path=candidate,
            )
            return

        try:
            self.backend = self._backend_factory(None)
        except Exception as error:
            self.backend = None
            self._backend_note = 'Native USB backend resolution failed: {error}'.format(
                error=error,
            )
            return

        if self.backend is not None:
            self._backend_note = 'Native USB backend resolved through the platform libusb loader.'
            return
        self._backend_note = 'Bundled libusb backend was not found in packaged assets.'

    def _candidate_backend_paths(
        self,
        backend_path: Optional[Path],
    ) -> Tuple[Path, ...]:
        """Return the candidate libusb DLL paths for Windows detection."""

        candidates = []
        if backend_path is not None:
            candidates.append(Path(backend_path))
        candidates.append(WINDOWS_BACKEND_DLL)
        unique_candidates = []
        for candidate in candidates:
            resolved = Path(candidate)
            if resolved not in unique_candidates and resolved.exists():
                unique_candidates.append(resolved)
        return tuple(unique_candidates)

    def _default_backend_factory(self, library_path: Optional[str]):
        """Resolve one libusb backend instance for pyusb."""

        if _usb_backend_libusb1 is None:
            return None
        if library_path:
            ctypes.WinDLL(library_path)
            return _usb_backend_libusb1.get_backend(
                find_library=lambda _name: library_path,
            )
        return _usb_backend_libusb1.get_backend()

    def _matches_supported_download_mode_device(self, device) -> bool:
        """Return whether the raw USB device matches the supported registry."""

        try:
            product_id = int(getattr(device, 'idProduct', -1))
        except Exception:
            return False
        return product_id in SAMSUNG_DOWNLOAD_MODE_PRODUCT_IDS

    def _normalize_device(
        self,
        device,
        read_identity_strings: bool = True,
    ) -> _NormalizedUSBDevice:
        """Normalize one raw pyusb device into a stable descriptor surface."""

        bus = getattr(device, 'bus', None)
        address = getattr(device, 'address', None)
        fallback_serial = 'usb-{bus}-{address}'.format(
            bus=(bus if bus is not None else 'unknownbus'),
            address=(address if address is not None else 'unknownaddr'),
        )
        serial_number = fallback_serial
        manufacturer = 'Samsung'
        product_name = SAMSUNG_DOWNLOAD_MODE_PRODUCT_IDS.get(
            int(getattr(device, 'idProduct', 0)),
            'Samsung download device',
        )
        product_code = None
        serial_issue = False
        manufacturer_issue = False
        product_issue = False
        if read_identity_strings:
            serial_number, serial_issue = self._read_descriptor_string(
                device,
                direct_attribute='serial_number',
                index_attribute='iSerialNumber',
            )
            manufacturer, manufacturer_issue = self._read_descriptor_string(
                device,
                direct_attribute='manufacturer',
                index_attribute='iManufacturer',
            )
            product_name, product_issue = self._read_descriptor_string(
                device,
                direct_attribute='product',
                index_attribute='iProduct',
            )
            product_code = self._extract_product_code(product_name, serial_number)
        notes = []  # type: list[str]
        if any((serial_issue, manufacturer_issue, product_issue)):
            notes.append(
                'One or more USB identity strings could not be read through the current access path; continuing with bounded download-mode presence only.'
            )
        return _NormalizedUSBDevice(
            descriptor=USBDeviceDescriptor(
                vendor_id=int(getattr(device, 'idVendor', SAMSUNG_VENDOR_ID)),
                product_id=int(getattr(device, 'idProduct', 0)),
                bus=(int(bus) if bus is not None else None),
                address=(int(address) if address is not None else None),
                serial_number=serial_number or fallback_serial,
                manufacturer=manufacturer,
                product_name=product_name,
                product_code=product_code,
                command_ready=True,
            ),
            notes=tuple(notes),
        )

    def _read_descriptor_string(
        self,
        device,
        direct_attribute: str,
        index_attribute: str,
    ) -> Tuple[Optional[str], bool]:
        """Read one descriptor string from a raw USB device."""

        try:
            direct_raw_value = getattr(device, direct_attribute, None)
        except Exception as error:
            self.logger.warning(
                'Native USB descriptor read for %s raised %s; '
                'continuing with bounded attention semantics.',
                direct_attribute,
                error,
            )
            return None, True
        direct_value = _normalize_text(direct_raw_value)
        if direct_value is not None:
            return direct_value, False
        index = getattr(device, index_attribute, None)
        if not index or self._usb_util is None or not hasattr(self._usb_util, 'get_string'):
            return None, False
        try:
            value = self._usb_util.get_string(device, index)
        except Exception as error:
            self.logger.warning(
                'Native USB indexed descriptor read for %s raised %s; '
                'continuing with bounded attention semantics.',
                direct_attribute,
                error,
            )
            return None, True
        return _normalize_text(value), False

    def _extract_product_code(self, *values: Optional[str]) -> Optional[str]:
        """Extract one Samsung product code from descriptor text when available."""

        for value in values:
            if value is None:
                continue
            match = PRODUCT_CODE_PATTERN.search(value)
            if match is None:
                continue
            return match.group(0).upper().replace('_', '-')
        return None

    def _requires_platform_remediation(self, error: Exception) -> bool:
        """Return whether the USB error suggests driver/backend remediation."""

        message = str(error).lower()
        return any(
            token in message
            for token in (
                'no backend',
                'backend not found',
                'access denied',
                'permission denied',
                'insufficient permissions',
                'operation not permitted',
                'libusb',
                'driver',
            )
        )

    def _elevation_command(self, reason: Optional[str]) -> Optional[Sequence[str]]:
        """Build the packaged helper command for the current platform."""

        normalized_reason = (reason or 'USB remediation requested.').replace("'", "''")
        if self._platform_name.startswith('win'):
            if not WINDOWS_INJECTOR_SCRIPT.exists():
                return None
            command = (
                "Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList @(" 
                "'-NoProfile','-ExecutionPolicy','Bypass','-File',"
                "'{script}','-VendorId','0x{vendor:04X}','-ProductId','0x{product:04X}','-Reason','{reason}')"
            ).format(
                script=str(WINDOWS_INJECTOR_SCRIPT).replace("'", "''"),
                vendor=SAMSUNG_VENDOR_ID,
                product=min(SAMSUNG_DOWNLOAD_MODE_PRODUCT_IDS.keys()),
                reason=normalized_reason,
            )
            return (
                'powershell.exe',
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-Command',
                command,
            )

        if not LINUX_INJECTOR_SCRIPT.exists():
            return None
        if shutil.which('pkexec') is not None:
            return (
                'pkexec',
                str(LINUX_INJECTOR_SCRIPT),
                '--vendor-id',
                '0x{vendor:04X}'.format(vendor=SAMSUNG_VENDOR_ID),
                '--product-id',
                '0x{product:04X}'.format(
                    product=min(SAMSUNG_DOWNLOAD_MODE_PRODUCT_IDS.keys()),
                ),
            )
        if shutil.which('sudo') is not None:
            return (
                'sudo',
                str(LINUX_INJECTOR_SCRIPT),
                '--vendor-id',
                '0x{vendor:04X}'.format(vendor=SAMSUNG_VENDOR_ID),
                '--product-id',
                '0x{product:04X}'.format(
                    product=min(SAMSUNG_DOWNLOAD_MODE_PRODUCT_IDS.keys()),
                ),
            )
        return (str(LINUX_INJECTOR_SCRIPT),)

    @staticmethod
    def _default_elevation_runner(command: Sequence[str]) -> None:
        """Launch one remediation helper without blocking the caller."""

        subprocess.Popen(command)

    @staticmethod
    def _display_command(command: Sequence[str]) -> str:
        """Render one process command for logs and test assertions."""

        return ' '.join(str(part) for part in command)

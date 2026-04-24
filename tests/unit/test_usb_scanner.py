"""Unit tests for the native USB scanner contract."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest import mock


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

from calamum_vulcan.usb import VulcanUSBScanner
from calamum_vulcan.usb import scanner as usb_scanner_module
from tests.mocks.mock_usb import MockBackend
from tests.mocks.mock_usb import MockDevice
from tests.mocks.mock_usb import MockUSBCore
from tests.mocks.mock_usb import MockUSBError
from tests.mocks.mock_usb import MockUSBUtil


class _LangIdDirectPropertyDevice:
  """Simulate one pyusb device whose descriptor properties raise LANGID errors."""

  def __init__(self, error: Exception) -> None:
    self.idVendor = 0x04E8
    self.idProduct = 0x685D
    self.bus = 1
    self.address = 4
    self.iSerialNumber = 1
    self.iManufacturer = 2
    self.iProduct = 3
    self._error = error

  @property
  def serial_number(self):
    raise self._error

  @property
  def manufacturer(self):
    raise self._error

  @property
  def product(self):
    raise self._error


class USBScannerContractTests(unittest.TestCase):
  """Prove the Sprint 0.5.0 native USB seam stays deterministic and testable."""

  def test_scanner_detects_supported_download_mode_device(self) -> None:
    scanner = VulcanUSBScanner(
      usb_core_module=MockUSBCore(
        devices=(
          MockDevice(
            idVendor=0x04E8,
            idProduct=0x685D,
            bus=1,
            address=4,
            serial_number='usb-g991u-lab-01',
            manufacturer='Samsung',
            product='Samsung Galaxy S21 (SM-G991U)',
          ),
        )
      ),
      usb_util_module=MockUSBUtil,
      backend_factory=lambda _path: MockBackend(),
      platform_name='win32',
    )

    probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'detected')
    self.assertEqual(len(probe_result.devices), 1)
    self.assertEqual(probe_result.devices[0].product_code, 'SM-G991U')
    self.assertEqual(probe_result.devices[0].serial_number, 'usb-g991u-lab-01')
    self.assertIn('bundled libusb', ' '.join(probe_result.notes).lower())

  def test_scanner_returns_cleared_when_no_device_is_present(self) -> None:
    scanner = VulcanUSBScanner(
      usb_core_module=MockUSBCore(devices=()),
      usb_util_module=MockUSBUtil,
      backend_factory=lambda _path: MockBackend(),
      platform_name='linux',
    )

    probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'cleared')
    self.assertEqual(probe_result.devices, ())
    self.assertIn('did not detect', probe_result.summary.lower())

  def test_scanner_keeps_detected_download_mode_ready_when_usb_identity_strings_need_help(self) -> None:
    device = MockDevice(
      idVendor=0x04E8,
      idProduct=0x685D,
      bus=1,
      address=4,
      serial_number='usb-g991u-lab-02',
      manufacturer=None,
      product='Samsung Galaxy S21 (SM-G991U)',
    )
    device.iManufacturer = 2

    class _FailingUSBUtil:
      @staticmethod
      def get_string(_device, _index):
        raise MockUSBError('access denied to libusb backend')

    scanner = VulcanUSBScanner(
      usb_core_module=MockUSBCore(devices=(device,)),
      usb_util_module=_FailingUSBUtil,
      backend_factory=lambda _path: MockBackend(),
      platform_name='linux',
    )

    probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'detected')
    self.assertEqual(len(probe_result.devices), 1)
    self.assertTrue(probe_result.devices[0].command_ready)
    self.assertIn('download-mode presence only', ' '.join(probe_result.notes).lower())

  def test_scanner_treats_no_langid_descriptor_errors_as_detected_identity_incomplete(self) -> None:
    descriptor_error = MockUSBError(
      'The device has no langid (permission issue, no string descriptors supported or device error)'
    )

    class _LangIdFailingUSBUtil:
      @staticmethod
      def get_string(_device, _index):
        raise descriptor_error

    scanner = VulcanUSBScanner(
      usb_core_module=MockUSBCore(
        devices=(
          _LangIdDirectPropertyDevice(descriptor_error),
        )
      ),
      usb_util_module=_LangIdFailingUSBUtil,
      backend_factory=lambda _path: MockBackend(),
      platform_name='win32',
    )

    probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'detected')
    self.assertEqual(len(probe_result.devices), 1)
    self.assertTrue(probe_result.devices[0].command_ready)
    self.assertEqual(probe_result.devices[0].serial_number, 'usb-1-4')
    self.assertIsNone(probe_result.devices[0].manufacturer)
    self.assertIsNone(probe_result.devices[0].product_name)
    self.assertIn('download-mode presence only', ' '.join(probe_result.notes).lower())
    self.assertIn('read pit', ' '.join(probe_result.notes).lower())

  def test_scanner_can_skip_identity_string_reads_for_presence_only_detection(self) -> None:
    descriptor_error = MockUSBError('descriptor access should not be attempted')
    scanner = VulcanUSBScanner(
      usb_core_module=MockUSBCore(
        devices=(
          _LangIdDirectPropertyDevice(descriptor_error),
        )
      ),
      usb_util_module=MockUSBUtil,
      backend_factory=lambda _path: MockBackend(),
      platform_name='win32',
    )

    probe_result = scanner.probe_download_mode_devices(read_identity_strings=False)

    self.assertEqual(probe_result.state, 'detected')
    self.assertEqual(len(probe_result.devices), 1)
    self.assertEqual(probe_result.devices[0].serial_number, 'usb-1-4')
    self.assertEqual(probe_result.devices[0].manufacturer, 'Samsung')
    self.assertEqual(probe_result.devices[0].product_name, 'Samsung download mode')
    self.assertIsNone(probe_result.devices[0].product_code)
    self.assertNotIn('download-mode presence only', ' '.join(probe_result.notes).lower())

  def test_scanner_requests_windows_remediation_when_backend_is_missing(self) -> None:
    launched = []
    scanner = VulcanUSBScanner(
      usb_core_module=MockUSBCore(devices=()),
      usb_util_module=MockUSBUtil,
      backend_factory=lambda _path: None,
      elevation_runner=lambda command: launched.append(tuple(command)),
      platform_name='win32',
    )

    probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'failed')
    self.assertIsNotNone(probe_result.remediation_command)
    self.assertTrue(launched)
    self.assertIn('powershell.exe', probe_result.remediation_command)

  def test_scanner_requests_remediation_for_usb_access_errors(self) -> None:
    launched = []
    scanner = VulcanUSBScanner(
      usb_core_module=MockUSBCore(
        error=MockUSBError('access denied to libusb backend')
      ),
      usb_util_module=MockUSBUtil,
      backend_factory=lambda _path: MockBackend(),
      elevation_runner=lambda command: launched.append(tuple(command)),
      platform_name='linux',
    )

    probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'failed')
    self.assertIsNotNone(probe_result.remediation_command)
    self.assertTrue(launched)
    self.assertIn('udev_injector.sh', probe_result.remediation_command)

  def test_scanner_repairs_missing_runtime_dependencies_before_continuing(self) -> None:
    scanner = VulcanUSBScanner(
      usb_core_module=None,
      usb_util_module=None,
      backend_factory=lambda _path: MockBackend(),
      platform_name='linux',
    )
    scanner._usb_core = None
    scanner._usb_util = None

    with mock.patch.object(
      usb_scanner_module,
      'attempt_runtime_dependency_repair',
      return_value=(
        'Automatic runtime dependency repair refreshed Calamum Vulcan from '
        'the source checkout and satisfied the declared runtime dependency '
        'set for this environment.'
      ),
    ), mock.patch.object(
      usb_scanner_module,
      '_import_pyusb_modules',
      return_value=(object(), MockUSBCore(devices=()), MockUSBUtil, None),
    ):
      probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'cleared')
    self.assertIn(
      'Automatic runtime dependency repair refreshed Calamum Vulcan',
      ' '.join(probe_result.notes),
    )

  def test_scanner_surfaces_runtime_dependency_repair_failure(self) -> None:
    scanner = VulcanUSBScanner(
      usb_core_module=None,
      usb_util_module=None,
      backend_factory=lambda _path: MockBackend(),
      platform_name='linux',
    )
    scanner._usb_core = None
    scanner._usb_util = None

    with mock.patch.object(
      usb_scanner_module,
      'attempt_runtime_dependency_repair',
      return_value=(
        'Automatic runtime dependency repair failed in this environment: '
        'offline wheel was unavailable.'
      ),
    ), mock.patch.object(
      usb_scanner_module,
      '_import_pyusb_modules',
      return_value=(None, None, None, 'No module named usb'),
    ):
      probe_result = scanner.probe_download_mode_devices()

    self.assertEqual(probe_result.state, 'failed')
    self.assertIn('runtime dependency set is still incomplete', probe_result.summary.lower())
    self.assertIn(
      'Automatic runtime dependency repair failed in this environment',
      ' '.join(probe_result.notes),
    )


if __name__ == '__main__':
  unittest.main()

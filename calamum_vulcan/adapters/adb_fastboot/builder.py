"""Command-plan builders for the Calamum Vulcan ADB/Fastboot companion seam."""

from __future__ import annotations

from typing import Optional
from typing import Tuple

from .model import AdbRebootTarget
from .model import AndroidToolsBackend
from .model import AndroidToolsCapability
from .model import AndroidToolsCommandPlan
from .model import AndroidToolsOperation
from .model import FastbootRebootTarget


DOWNLOAD_MODE_NOTE = (
  'Samsung download-mode reboot through adb is vendor-specific and must stay '
  'behind hardware validation on the supported device matrix.',
)


def available_adb_reboot_targets() -> Tuple[str, ...]:
  """Return the supported ADB reboot targets in display order."""

  return tuple(target.value for target in AdbRebootTarget)


def available_fastboot_reboot_targets() -> Tuple[str, ...]:
  """Return the supported Fastboot reboot targets in display order."""

  return tuple(target.value for target in FastbootRebootTarget)


def build_adb_detect_command_plan(
  device_serial: Optional[str] = None,
) -> AndroidToolsCommandPlan:
  """Build the sanctioned `adb devices -l` command plan."""

  arguments = _prefixed_serial_arguments(device_serial) + ('devices', '-l')
  return _command_plan(
    AndroidToolsCapability.DETECT_ADB_DEVICES,
    AndroidToolsOperation.ADB_DEVICES,
    AndroidToolsBackend.ADB,
    arguments,
    target_serial=device_serial,
  )


def build_fastboot_detect_command_plan(
  device_serial: Optional[str] = None,
) -> AndroidToolsCommandPlan:
  """Build the sanctioned `fastboot devices` command plan."""

  arguments = _prefixed_serial_arguments(device_serial) + ('devices',)
  return _command_plan(
    AndroidToolsCapability.DETECT_FASTBOOT_DEVICES,
    AndroidToolsOperation.FASTBOOT_DEVICES,
    AndroidToolsBackend.FASTBOOT,
    arguments,
    target_serial=device_serial,
  )


def build_adb_reboot_command_plan(
  target: str,
  device_serial: Optional[str] = None,
) -> AndroidToolsCommandPlan:
  """Build the sanctioned `adb reboot <target>` command plan."""

  reboot_target = AdbRebootTarget(target)
  arguments = _prefixed_serial_arguments(device_serial) + ('reboot',)
  notes = ()
  vendor_specific = False
  if reboot_target != AdbRebootTarget.SYSTEM:
    arguments += (reboot_target.value,)
  if reboot_target == AdbRebootTarget.DOWNLOAD:
    vendor_specific = True
    notes = DOWNLOAD_MODE_NOTE
  return _command_plan(
    AndroidToolsCapability.REBOOT_TO_MODE,
    AndroidToolsOperation.ADB_REBOOT,
    AndroidToolsBackend.ADB,
    arguments,
    target_serial=device_serial,
    reboot_target=reboot_target.value,
    vendor_specific=vendor_specific,
    notes=notes,
  )


def build_fastboot_reboot_command_plan(
  target: str,
  device_serial: Optional[str] = None,
) -> AndroidToolsCommandPlan:
  """Build the sanctioned `fastboot reboot` command plan."""

  reboot_target = FastbootRebootTarget(target)
  arguments = _prefixed_serial_arguments(device_serial) + ('reboot',)
  if reboot_target == FastbootRebootTarget.BOOTLOADER:
    arguments += ('bootloader',)
  return _command_plan(
    AndroidToolsCapability.REBOOT_TO_MODE,
    AndroidToolsOperation.FASTBOOT_REBOOT,
    AndroidToolsBackend.FASTBOOT,
    arguments,
    target_serial=device_serial,
    reboot_target=reboot_target.value,
  )


def _prefixed_serial_arguments(device_serial: Optional[str]) -> Tuple[str, ...]:
  if device_serial is None:
    return ()
  return ('-s', device_serial)


def _command_plan(
  capability: AndroidToolsCapability,
  operation: AndroidToolsOperation,
  backend: AndroidToolsBackend,
  arguments: Tuple[str, ...],
  target_serial: Optional[str] = None,
  reboot_target: Optional[str] = None,
  vendor_specific: bool = False,
  notes: Tuple[str, ...] = (),
) -> AndroidToolsCommandPlan:
  display_command = ' '.join((backend.value,) + arguments)
  return AndroidToolsCommandPlan(
    capability=capability,
    operation=operation,
    backend=backend,
    executable=backend.value,
    arguments=arguments,
    display_command=display_command,
    target_serial=target_serial,
    reboot_target=reboot_target,
    vendor_specific=vendor_specific,
    notes=notes,
  )
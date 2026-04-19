"""ADB/Fastboot companion adapter contracts for Calamum Vulcan."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple


class AndroidToolsBackend(str, Enum):
  """Supported Android SDK platform-tool backends."""

  ADB = 'adb'
  FASTBOOT = 'fastboot'


class AndroidToolsCapability(str, Enum):
  """Bounded live-device capabilities exposed through the companion seam."""

  DETECT_ADB_DEVICES = 'detect_adb_devices'
  DETECT_FASTBOOT_DEVICES = 'detect_fastboot_devices'
  REBOOT_TO_MODE = 'reboot_to_mode'


class AndroidToolsOperation(str, Enum):
  """Concrete companion-tool operations represented by the adapter."""

  ADB_DEVICES = 'adb_devices'
  FASTBOOT_DEVICES = 'fastboot_devices'
  ADB_REBOOT = 'adb_reboot'
  FASTBOOT_REBOOT = 'fastboot_reboot'


class AndroidToolsTraceState(str, Enum):
  """Operator-facing states emitted by the companion adapter seam."""

  DETECTED = 'detected'
  NO_DEVICES = 'no_devices'
  COMPLETED = 'completed'
  FAILED = 'failed'
  NOT_INVOKED = 'not_invoked'


class AdbRebootTarget(str, Enum):
  """ADB reboot targets exposed by the companion control surface."""

  SYSTEM = 'system'
  BOOTLOADER = 'bootloader'
  RECOVERY = 'recovery'
  SIDELOAD = 'sideload'
  SIDELOAD_AUTO_REBOOT = 'sideload-auto-reboot'
  DOWNLOAD = 'download'


class FastbootRebootTarget(str, Enum):
  """Fastboot reboot targets exposed in the initial companion lane."""

  SYSTEM = 'system'
  BOOTLOADER = 'bootloader'


@dataclass(frozen=True)
class AndroidDeviceRecord:
  """One device surfaced by `adb devices -l` or `fastboot devices`."""

  serial: str
  state: str
  transport: str
  product: Optional[str] = None
  model: Optional[str] = None
  device: Optional[str] = None


@dataclass(frozen=True)
class AndroidToolsCommandPlan:
  """One bounded companion-tool command assembled by the platform."""

  capability: AndroidToolsCapability
  operation: AndroidToolsOperation
  backend: AndroidToolsBackend
  executable: str
  arguments: Tuple[str, ...]
  display_command: str
  target_serial: Optional[str] = None
  reboot_target: Optional[str] = None
  vendor_specific: bool = False
  expected_exit_codes: Tuple[int, ...] = (0,)
  notes: Tuple[str, ...] = ()

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this command plan."""

    return asdict(self)


@dataclass(frozen=True)
class AndroidToolsProcessResult:
  """Mocked or live process result returned by the companion boundary."""

  fixture_name: str
  operation: AndroidToolsOperation
  backend: AndroidToolsBackend
  exit_code: int
  stdout_lines: Tuple[str, ...] = ()
  stderr_lines: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AndroidToolsNormalizedTrace:
  """Normalized detection or control trace produced by the companion seam."""

  fixture_name: str
  command_plan: AndroidToolsCommandPlan
  state: AndroidToolsTraceState
  summary: str
  exit_code: int
  detected_devices: Tuple[AndroidDeviceRecord, ...] = ()
  notes: Tuple[str, ...] = ()
  stdout_lines: Tuple[str, ...] = ()
  stderr_lines: Tuple[str, ...] = ()

  def to_dict(self) -> Dict[str, Any]:
    """Return a JSON-serializable dictionary for this normalized trace."""

    return asdict(self)
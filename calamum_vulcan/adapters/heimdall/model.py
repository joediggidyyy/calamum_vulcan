"""Heimdall adapter contracts for the Calamum Vulcan FS-07 lane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from calamum_vulcan.domain.state.model import PlatformEvent


class HeimdallCapability(str, Enum):
  """Backend capabilities the platform is allowed to expose in Sprint 0.1.0."""

  DETECT_DEVICE = 'detect_device'
  FLASH_PACKAGE = 'flash_package'
  PRINT_PIT = 'print_pit'
  DOWNLOAD_PIT = 'download_pit'


class HeimdallOperation(str, Enum):
  """Concrete Heimdall operations represented by the adapter seam."""

  DETECT = 'detect'
  FLASH = 'flash'
  PRINT_PIT = 'print_pit'
  DOWNLOAD_PIT = 'download_pit'


class HeimdallTraceState(str, Enum):
  """Operator-facing transport states emitted by the Heimdall adapter seam."""

  DETECTED = 'detected'
  EXECUTING = 'executing'
  RESUME_NEEDED = 'resume_needed'
  COMPLETED = 'completed'
  FAILED = 'failed'
  NOT_INVOKED = 'not_invoked'


@dataclass(frozen=True)
class HeimdallCommandPlan:
  """One backend invocation plan constructed by the platform-owned adapter."""

  capability: HeimdallCapability
  operation: HeimdallOperation
  executable: str
  arguments: Tuple[str, ...]
  display_command: str
  expected_exit_codes: Tuple[int, ...] = (0,)


@dataclass(frozen=True)
class HeimdallProcessResult:
  """Mocked or live process result returned by the backend boundary."""

  fixture_name: str
  operation: HeimdallOperation
  exit_code: int
  stdout_lines: Tuple[str, ...] = ()
  stderr_lines: Tuple[str, ...] = ()


@dataclass(frozen=True)
class HeimdallNormalizedTrace:
  """Normalized transport trace produced from one Heimdall process result."""

  fixture_name: str
  command_plan: HeimdallCommandPlan
  state: HeimdallTraceState
  summary: str
  exit_code: int
  platform_events: Tuple[PlatformEvent, ...]
  progress_markers: Tuple[str, ...] = ()
  notes: Tuple[str, ...] = ()
  stdout_lines: Tuple[str, ...] = ()
  stderr_lines: Tuple[str, ...] = ()
  adapter_name: str = 'heimdall'

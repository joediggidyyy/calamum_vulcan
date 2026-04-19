"""Preflight models for the Calamum Vulcan FS-04 trust gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import SessionPhase


class PreflightSeverity(str, Enum):
  """Severity of one preflight signal."""

  PASS = 'pass'
  WARN = 'warn'
  BLOCK = 'block'


class PreflightGate(str, Enum):
  """Operator-visible state of the preflight gate."""

  READY = 'ready'
  WARN = 'warn'
  BLOCKED = 'blocked'


class PreflightCategory(str, Enum):
  """Functional preflight groupings shown in the shell."""

  HOST = 'host'
  DEVICE = 'device'
  PACKAGE = 'package'
  COMPATIBILITY = 'compatibility'
  SAFETY = 'safety'


@dataclass(frozen=True)
class PreflightSignal:
  """One deterministic preflight rule result."""

  rule_id: str
  category: PreflightCategory
  severity: PreflightSeverity
  title: str
  summary: str
  remediation: str


@dataclass(frozen=True)
class PreflightInput:
  """Inputs required to evaluate the sprint preflight board."""

  device_present: bool = False
  in_download_mode: bool = False
  host_ready: bool = True
  driver_ready: bool = True
  package_selected: bool = False
  package_complete: bool = False
  checksums_present: bool = False
  product_code_match: bool = False
  warnings_acknowledged: bool = False
  destructive_operation: bool = False
  destructive_acknowledged: bool = False
  battery_level: Optional[int] = None
  cable_quality: str = 'known_good'
  reboot_mode: str = 'standard'
  product_code: Optional[str] = None
  package_id: Optional[str] = None
  session_phase: Optional[SessionPhase] = None
  notes: Tuple[str, ...] = ()

  @classmethod
  def from_session(
    cls,
    session: PlatformSession,
    **overrides: object,
  ) -> 'PreflightInput':
    """Build a conservative preflight input snapshot from session state."""

    defaults = {
      'device_present': session.guards.has_device,
      'in_download_mode': session.mode == 'download',
      'host_ready': True,
      'driver_ready': True,
      'package_selected': session.guards.package_loaded,
      'package_complete': session.guards.package_loaded,
      'checksums_present': session.guards.package_loaded,
      'product_code_match': bool(session.product_code)
      and session.phase != SessionPhase.VALIDATION_BLOCKED,
      'warnings_acknowledged': session.guards.warnings_acknowledged,
      'destructive_operation': session.guards.operation_is_destructive,
      'destructive_acknowledged': session.guards.destructive_acknowledged,
      'battery_level': 72 if session.guards.has_device else None,
      'cable_quality': 'known_good',
      'reboot_mode': _infer_reboot_mode(session),
      'product_code': session.product_code,
      'package_id': session.package_id,
      'session_phase': session.phase,
      'notes': session.preflight_notes,
    }
    defaults.update(overrides)
    return cls(**defaults)


@dataclass(frozen=True)
class PreflightReport:
  """Evaluated preflight report consumed by the GUI shell."""

  gate: PreflightGate
  signals: Tuple[PreflightSignal, ...]
  ready_for_execution: bool
  summary: str
  recommended_action: str
  pass_count: int
  warning_count: int
  block_count: int


def _infer_reboot_mode(session: PlatformSession) -> str:
  notes = ' '.join(session.preflight_notes).lower()
  if session.phase == SessionPhase.RESUME_NEEDED:
    return 'no_reboot'
  if 'manual recovery boot required' in notes:
    return 'no_reboot'
  return 'standard'
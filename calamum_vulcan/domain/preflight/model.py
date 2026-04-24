"""Preflight models for the Calamum Vulcan FS-04 trust gate."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.domain.live_device.model import LiveDeviceSource
from calamum_vulcan.domain.state.model import PlatformSession
from calamum_vulcan.domain.state.model import SessionPhase


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
  snapshot_required: bool = False
  snapshot_created: bool = False
  snapshot_verified: bool = False
  snapshot_drift_detected: bool = False
  device_registry_known: bool = False
  device_registry_match_kind: DeviceRegistryMatchKind = DeviceRegistryMatchKind.NOT_PROVIDED
  product_code_match: bool = False
  warnings_acknowledged: bool = False
  destructive_operation: bool = False
  destructive_acknowledged: bool = False
  battery_level: Optional[int] = None
  cable_quality: str = 'known_good'
  reboot_mode: str = 'standard'
  product_code: Optional[str] = None
  canonical_product_code: Optional[str] = None
  device_marketing_name: Optional[str] = None
  device_mode_entry_instructions: Tuple[str, ...] = ()
  device_known_quirks: Tuple[str, ...] = ()
  package_id: Optional[str] = None
  snapshot_id: Optional[str] = None
  suspicious_warning_count: int = 0
  suspiciousness_summary: str = 'No suspicious Android traits detected.'
  suspicious_indicator_ids: Tuple[str, ...] = ()
  session_phase: Optional[SessionPhase] = None
  notes: Tuple[str, ...] = ()
  pit_required: bool = False
  pit_state: Optional[str] = None
  pit_summary: Optional[str] = None
  pit_package_alignment: Optional[str] = None
  pit_device_alignment: Optional[str] = None
  pit_observed_product_code: Optional[str] = None
  device_identity_review_deferred: bool = False
  package_review_deferred: bool = False

  @classmethod
  def from_session(
    cls,
    session: PlatformSession,
    **overrides: object,
  ) -> 'PreflightInput':
    """Build a conservative preflight input snapshot from session state."""

    registry_resolution = resolve_device_profile(session.product_code)
    defaults = {
      'device_present': session.guards.has_device,
      'in_download_mode': session.mode == 'download',
      'host_ready': True,
      'driver_ready': True,
      'package_selected': session.guards.package_loaded,
      'package_complete': session.guards.package_loaded,
      'checksums_present': session.guards.package_loaded,
      'snapshot_required': False,
      'snapshot_created': False,
      'snapshot_verified': False,
      'snapshot_drift_detected': False,
      'device_registry_known': registry_resolution.known,
      'device_registry_match_kind': registry_resolution.match_kind,
      'product_code_match': bool(registry_resolution.detected_product_code)
      and session.phase != SessionPhase.VALIDATION_BLOCKED,
      'warnings_acknowledged': session.guards.warnings_acknowledged,
      'destructive_operation': session.guards.operation_is_destructive,
      'destructive_acknowledged': session.guards.destructive_acknowledged,
      'battery_level': 72 if session.guards.has_device else None,
      'cable_quality': 'known_good',
      'reboot_mode': _infer_reboot_mode(session),
      'product_code': registry_resolution.detected_product_code,
      'canonical_product_code': registry_resolution.canonical_product_code,
      'device_marketing_name': registry_resolution.marketing_name,
      'device_mode_entry_instructions': registry_resolution.mode_entry_instructions,
      'device_known_quirks': registry_resolution.known_quirks,
      'package_id': session.package_id,
      'snapshot_id': None,
      'suspicious_warning_count': 0,
      'suspiciousness_summary': 'No suspicious Android traits detected.',
      'suspicious_indicator_ids': (),
      'session_phase': session.phase,
      'notes': session.preflight_notes,
      'pit_required': False,
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


def preflight_overrides_from_review_context(
  package_assessment: Optional[object] = None,
  pit_inspection: Optional[object] = None,
  pit_required: bool = False,
) -> Dict[str, object]:
  """Merge package and PIT truth into one preflight-override dictionary."""

  overrides = {}  # type: Dict[str, object]
  if pit_required:
    overrides['pit_required'] = True
  if package_assessment is not None:
    from calamum_vulcan.domain.package import preflight_overrides_from_package_assessment

    overrides.update(
      preflight_overrides_from_package_assessment(package_assessment)
    )
  if pit_inspection is not None:
    from calamum_vulcan.domain.pit import preflight_overrides_from_pit_inspection

    overrides.update(
      preflight_overrides_from_pit_inspection(pit_inspection)
    )
  return overrides


def preflight_input_from_review_context(
  session: PlatformSession,
  package_assessment: Optional[object] = None,
  pit_inspection: Optional[object] = None,
  pit_required: bool = False,
) -> 'PreflightInput':
  """Build one preflight input snapshot from reviewed package and PIT truth."""

  overrides = preflight_overrides_from_review_context(
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    pit_required=pit_required,
  )
  effective_product_code = _effective_review_product_code(session, overrides)
  if effective_product_code is None:
    pit_product_code = _pit_review_product_code(pit_inspection)
    if pit_product_code is not None:
      resolution = resolve_device_profile(pit_product_code)
      overrides.update(
        {
          'product_code': pit_product_code,
          'device_registry_known': resolution.known,
          'device_registry_match_kind': resolution.match_kind,
          'canonical_product_code': resolution.canonical_product_code,
          'device_marketing_name': resolution.marketing_name,
        }
      )
      effective_product_code = pit_product_code
  if _download_mode_review_active(session) and not _pit_capture_complete_for_package_stage(
    pit_inspection
  ):
    if effective_product_code is None:
      overrides['device_identity_review_deferred'] = True
    if package_assessment is None and not session.guards.package_loaded:
      overrides['package_review_deferred'] = True
  return PreflightInput.from_session(
    session,
    **overrides
  )


def _download_mode_review_active(session: PlatformSession) -> bool:
  """Return whether the current review lane is actively pinned on download mode."""

  snapshot = session.live_detection.snapshot
  if snapshot is not None:
    return bool(
      snapshot.source in (
        LiveDeviceSource.USB,
        LiveDeviceSource.HEIMDALL,
      )
      and snapshot.command_ready
    )
  return bool(
    session.guards.has_device and (session.mode or '').strip().lower() == 'download'
  )


def _pit_capture_complete_for_package_stage(
  pit_inspection: Optional[object],
) -> bool:
  """Return whether PIT truth is complete enough to unlock package staging."""

  if pit_inspection is None:
    return False
  pit_state = _enum_value(getattr(pit_inspection, 'state', None))
  pit_device_alignment = _enum_value(
    getattr(pit_inspection, 'device_alignment', None)
  )
  return pit_state == 'captured' and pit_device_alignment != 'not_provided'


def _pit_review_product_code(pit_inspection: Optional[object]) -> Optional[str]:
  """Return the strongest product-code truth currently available from PIT review."""

  if pit_inspection is None:
    return None
  return _normalized_string(
    getattr(pit_inspection, 'canonical_product_code', None)
    or getattr(pit_inspection, 'observed_product_code', None)
  )


def _effective_review_product_code(
  session: PlatformSession,
  overrides: Dict[str, object],
) -> Optional[str]:
  """Return the best current reviewed product code from session or overrides."""

  return _normalized_string(overrides.get('product_code')) or _normalized_string(
    session.product_code
  )


def _normalized_string(value: object) -> Optional[str]:
  """Return one stripped string value or None."""

  if value is None:
    return None
  normalized = str(value).strip()
  if not normalized:
    return None
  return normalized


def _enum_value(value: object) -> Optional[str]:
  """Return the string value of one enum-like object."""

  if value is None:
    return None
  return str(getattr(value, 'value', value))
"""Session-authority contracts for Calamum Vulcan Sprint 0.4.0 work."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.live_device.model import LiveDetectionState
from calamum_vulcan.domain.live_device.model import LiveDeviceSource
from calamum_vulcan.domain.live_device.model import LiveFallbackPosture
from calamum_vulcan.domain.safe_path import SafePathOwnership
from calamum_vulcan.domain.safe_path import SafePathReadiness

from .model import InspectionWorkflowPosture
from .model import PlatformSession
from .model import SessionPhase


SESSION_AUTHORITY_SCHEMA_VERSION = '0.4.0-fs4-01'
SESSION_AUTHORITY_SNAPSHOT_SCHEMA_VERSION = '0.4.0-fs4-02'


class SessionAuthorityPosture(str, Enum):
  """How explicitly Sprint 0.4.0 distinguishes competing session truths."""

  UNPINNED = 'unpinned'
  SPLIT = 'split'
  PINNED = 'pinned'
  STALE = 'stale'
  CONFLICTING = 'conflicting'


class SessionTruthSurface(str, Enum):
  """Named truth surfaces that must stay explicit during Sprint 0.4.0."""

  REVIEWED_SESSION = 'reviewed_session'
  LIVE_COMPANION = 'live_companion'
  INSPECTION_EVIDENCE = 'inspection_evidence'
  FALLBACK_STATUS = 'fallback_status'


class SessionLaunchPath(str, Enum):
  """Selected launch or review path derived from the authoritative session truth."""

  STANDBY = 'standby'
  REVIEW_ONLY = 'review_only'
  SAFE_PATH_CANDIDATE = 'safe_path_candidate'
  FALLBACK_REVIEW = 'fallback_review'
  BLOCKED = 'blocked'


class SessionRefreshState(str, Enum):
  """Whether the current session authority needs clear/refresh attention."""

  FRESH = 'fresh'
  REFRESH_RECOMMENDED = 'refresh_recommended'
  CLEAR_REQUIRED = 'clear_required'


@dataclass(frozen=True)
class SessionAuthorityContract:
  """Foundation contract for Sprint 0.4.0 session-authority work."""

  schema_version: str = SESSION_AUTHORITY_SCHEMA_VERSION
  posture: SessionAuthorityPosture = SessionAuthorityPosture.SPLIT
  truth_surfaces: Tuple[SessionTruthSurface, ...] = (
    SessionTruthSurface.REVIEWED_SESSION,
    SessionTruthSurface.LIVE_COMPANION,
    SessionTruthSurface.INSPECTION_EVIDENCE,
    SessionTruthSurface.FALLBACK_STATUS,
  )
  reviewed_truth_owner: str = 'calamum_vulcan.domain.state.PlatformSession'
  live_truth_owner: str = 'calamum_vulcan.domain.live_device.LiveDetectionSession'
  inspection_truth_owner: str = (
    'calamum_vulcan.domain.state.InspectionWorkflow'
  )
  summary: str = (
    'Sprint 0.4.0 keeps reviewed, live, inspection, and fallback truth '
    'explicit instead of flattening them into one ambiguous session banner.'
  )
  required_boundaries: Tuple[str, ...] = (
    'Reviewed session truth must remain explicit even when live companion truth is richer.',
    'Fallback status must remain operator-visible instead of hiding behind support wording.',
    'Inspection evidence must remain read-side truth until a narrower safe-path lane is explicitly owned.',
  )


@dataclass(frozen=True)
class SessionAuthoritySnapshot:
  """State-owned launch-state authority derived from reviewed/live session truth."""

  schema_version: str = SESSION_AUTHORITY_SNAPSHOT_SCHEMA_VERSION
  posture: SessionAuthorityPosture = SessionAuthorityPosture.PINNED
  reviewed_phase: str = SessionPhase.NO_DEVICE.value
  reviewed_phase_label: str = 'No Device'
  reviewed_target_label: str = 'No Download-Mode Target'
  reviewed_phase_tone: str = 'neutral'
  live_phase_label: str = 'No Device'
  live_phase_tone: str = 'neutral'
  selected_launch_path: SessionLaunchPath = SessionLaunchPath.STANDBY
  selected_launch_path_label: str = 'Standby'
  ownership: SafePathOwnership = SafePathOwnership.BLOCKED
  readiness: SafePathReadiness = SafePathReadiness.UNREVIEWED
  fallback_active: bool = False
  block_reason: Optional[str] = None
  refresh_state: SessionRefreshState = SessionRefreshState.FRESH
  refresh_reason: Optional[str] = None
  summary: str = (
    'Session authority is on standby until reviewed or live truth hydrates '
    'the current launch path.'
  )


PHASE_LABELS = {
  SessionPhase.NO_DEVICE: 'No Device',
  SessionPhase.DEVICE_DETECTED: 'Device Detected',
  SessionPhase.PREFLIGHT_INCOMPLETE: 'Preflight Incomplete',
  SessionPhase.PACKAGE_LOADED: 'Package Loaded',
  SessionPhase.VALIDATION_BLOCKED: 'Validation Blocked',
  SessionPhase.VALIDATION_PASSED: 'Validation Passed',
  SessionPhase.READY_TO_EXECUTE: 'Ready to Execute',
  SessionPhase.EXECUTING: 'Executing',
  SessionPhase.RESUME_NEEDED: 'Resume Needed',
  SessionPhase.COMPLETED: 'Completed',
  SessionPhase.FAILED: 'Failed',
}

PHASE_TONES = {
  SessionPhase.NO_DEVICE: 'neutral',
  SessionPhase.DEVICE_DETECTED: 'info',
  SessionPhase.PREFLIGHT_INCOMPLETE: 'warning',
  SessionPhase.PACKAGE_LOADED: 'info',
  SessionPhase.VALIDATION_BLOCKED: 'danger',
  SessionPhase.VALIDATION_PASSED: 'success',
  SessionPhase.READY_TO_EXECUTE: 'success',
  SessionPhase.EXECUTING: 'info',
  SessionPhase.RESUME_NEEDED: 'warning',
  SessionPhase.COMPLETED: 'success',
  SessionPhase.FAILED: 'danger',
}

LIVE_PHASE_LABELS = {
  LiveDeviceSource.ADB: 'ADB Device Detected',
  LiveDeviceSource.FASTBOOT: 'Fastboot Device Detected',
  LiveDeviceSource.USB: 'Download-Mode Device Detected',
  LiveDeviceSource.HEIMDALL: 'Download-Mode Device Detected',
}

LIVE_PHASE_ATTENTION_LABELS = {
  LiveDeviceSource.ADB: 'ADB Device Attention',
  LiveDeviceSource.FASTBOOT: 'Fastboot Device Attention',
  LiveDeviceSource.USB: 'Download-Mode Device Attention',
  LiveDeviceSource.HEIMDALL: 'Download-Mode Device Attention',
}

LAUNCH_PATH_LABELS = {
  SessionLaunchPath.STANDBY: 'Standby',
  SessionLaunchPath.REVIEW_ONLY: 'Review Only',
  SessionLaunchPath.SAFE_PATH_CANDIDATE: 'Safe-Path Candidate',
  SessionLaunchPath.FALLBACK_REVIEW: 'Fallback Review',
  SessionLaunchPath.BLOCKED: 'Blocked',
}


def build_session_authority_snapshot(
  session: PlatformSession,
  preflight_report: Optional[object] = None,
  package_assessment: Optional[object] = None,
  pit_inspection: Optional[object] = None,
  pit_required_for_safe_path: bool = False,
) -> SessionAuthoritySnapshot:
  """Derive the authoritative launch-state snapshot for the current session."""

  report = preflight_report or _default_preflight_report(
    session,
    package_assessment,
    pit_inspection,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  reviewed_phase_label = PHASE_LABELS[session.phase]
  reviewed_target_label = _reviewed_target_label(session)
  reviewed_phase_tone = PHASE_TONES[session.phase]
  live_phase_label, live_phase_tone = _live_phase(session)
  selected_launch_path = _selected_launch_path(
    session,
    report,
    package_assessment,
    pit_inspection,
    pit_required_for_safe_path,
  )
  ownership = _ownership_for_launch_path(session, selected_launch_path)
  readiness = _readiness_for_launch_path(
    session,
    report,
    selected_launch_path,
    pit_inspection,
    pit_required_for_safe_path,
  )
  fallback_active = (
    session.live_detection.fallback_posture != LiveFallbackPosture.NOT_NEEDED
  )
  block_reason = _block_reason(
    session,
    report,
    selected_launch_path,
    pit_inspection,
    pit_required_for_safe_path,
  )
  refresh_state, refresh_reason = _refresh_state(session)
  summary = _summary(
    session,
    selected_launch_path,
    ownership,
    readiness,
    block_reason,
    refresh_state,
  )
  return SessionAuthoritySnapshot(
    reviewed_phase=session.phase.value,
    reviewed_phase_label=reviewed_phase_label,
    reviewed_target_label=reviewed_target_label,
    reviewed_phase_tone=reviewed_phase_tone,
    live_phase_label=live_phase_label,
    live_phase_tone=live_phase_tone,
    selected_launch_path=selected_launch_path,
    selected_launch_path_label=LAUNCH_PATH_LABELS[selected_launch_path],
    ownership=ownership,
    readiness=readiness,
    fallback_active=fallback_active,
    block_reason=block_reason,
    refresh_state=refresh_state,
    refresh_reason=refresh_reason,
    summary=summary,
  )


def _default_preflight_report(
  session: PlatformSession,
  package_assessment: Optional[object],
  pit_inspection: Optional[object],
  pit_required_for_safe_path: bool = False,
) -> object:
  """Build a preflight report lazily to avoid a package-root import cycle."""

  from calamum_vulcan.domain.preflight import preflight_input_from_review_context
  from calamum_vulcan.domain.preflight import evaluate_preflight

  return evaluate_preflight(
    preflight_input_from_review_context(
      session,
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      pit_required=pit_required_for_safe_path,
    )
  )


def _live_phase(session: PlatformSession) -> Tuple[str, str]:
  """Return the operator-facing live phase label and tone."""

  snapshot = session.live_detection.snapshot
  if (
    session.phase in (SessionPhase.NO_DEVICE, SessionPhase.DEVICE_DETECTED)
    and not session.guards.package_loaded
    and snapshot is not None
  ):
    if session.live_detection.state == LiveDetectionState.ATTENTION:
      return LIVE_PHASE_ATTENTION_LABELS[snapshot.source], 'warning'
    if snapshot.command_ready:
      return LIVE_PHASE_LABELS[snapshot.source], 'info'
    return LIVE_PHASE_ATTENTION_LABELS[snapshot.source], 'warning'
  return PHASE_LABELS[session.phase], PHASE_TONES[session.phase]


def _reviewed_target_label(session: PlatformSession) -> str:
  """Return the explicit reviewed-target label with bounded target truth."""

  download_mode_target_label = _download_mode_review_target_label(session)
  if download_mode_target_label is not None:
    return download_mode_target_label
  if session.phase == SessionPhase.NO_DEVICE:
    return 'No Download-Mode Target'
  return PHASE_LABELS[session.phase]


def _download_mode_review_target_label(
  session: PlatformSession,
) -> Optional[str]:
  """Return a reviewed-target label when current truth is a real download-mode target."""

  if session.phase not in (
    SessionPhase.NO_DEVICE,
    SessionPhase.DEVICE_DETECTED,
  ):
    return None
  snapshot = session.live_detection.snapshot
  has_download_mode_target = bool(
    (
      snapshot is not None
      and snapshot.source in (
        LiveDeviceSource.USB,
        LiveDeviceSource.HEIMDALL,
      )
    )
    or (
      session.guards.has_device
      and (session.mode or '').strip().lower() == 'download'
    )
  )
  if not has_download_mode_target:
    return None
  if (
    session.live_detection.state == LiveDetectionState.ATTENTION
    or (snapshot is not None and not snapshot.command_ready)
  ):
    return 'Download-Mode Target Attention'
  return 'Download-Mode Target Detected'


def _selected_launch_path(
  session: PlatformSession,
  report: object,
  package_assessment: Optional[object],
  pit_inspection: Optional[object],
  pit_required_for_safe_path: bool,
) -> SessionLaunchPath:
  """Return the currently selected launch or review path."""

  if (
    _gate_value(report) == 'blocked'
    or _pit_hard_block(pit_inspection)
    or _pit_missing_required(
      session,
      pit_inspection,
      pit_required_for_safe_path,
    )
  ):
    if _fallback_active(session):
      return SessionLaunchPath.FALLBACK_REVIEW
    if not _has_review_inputs(session, package_assessment):
      return SessionLaunchPath.STANDBY
    return SessionLaunchPath.BLOCKED
  if session.phase in (
    SessionPhase.READY_TO_EXECUTE,
    SessionPhase.EXECUTING,
    SessionPhase.RESUME_NEEDED,
    SessionPhase.COMPLETED,
  ):
    return SessionLaunchPath.SAFE_PATH_CANDIDATE
  if _fallback_active(session):
    return SessionLaunchPath.FALLBACK_REVIEW
  if session.inspection.posture != InspectionWorkflowPosture.UNINSPECTED:
    return SessionLaunchPath.REVIEW_ONLY
  if _has_review_inputs(session, package_assessment):
    return SessionLaunchPath.REVIEW_ONLY
  return SessionLaunchPath.STANDBY


def _ownership_for_launch_path(
  session: PlatformSession,
  selected_launch_path: SessionLaunchPath,
) -> SafePathOwnership:
  """Return the current ownership classification for the selected path."""

  if selected_launch_path in (
    SessionLaunchPath.STANDBY,
    SessionLaunchPath.BLOCKED,
  ):
    return SafePathOwnership.BLOCKED
  if selected_launch_path == SessionLaunchPath.FALLBACK_REVIEW:
    return SafePathOwnership.FALLBACK
  if selected_launch_path == SessionLaunchPath.SAFE_PATH_CANDIDATE:
    return SafePathOwnership.DELEGATED
  live_path_ownership = getattr(
    getattr(session.live_detection.path_identity, 'ownership', None),
    'value',
    'none',
  )
  if live_path_ownership == 'fallback':
    return SafePathOwnership.FALLBACK
  if live_path_ownership == 'delegated':
    return SafePathOwnership.DELEGATED
  if (
    session.live_detection.snapshot is not None
    and session.live_detection.snapshot.source in (
      LiveDeviceSource.ADB,
      LiveDeviceSource.USB,
    )
    and session.live_detection.command_ready
  ):
    return SafePathOwnership.NATIVE
  return SafePathOwnership.DELEGATED


def _readiness_for_launch_path(
  session: PlatformSession,
  report: object,
  selected_launch_path: SessionLaunchPath,
  pit_inspection: Optional[object],
  pit_required_for_safe_path: bool,
) -> SafePathReadiness:
  """Return the current readiness posture for the selected path."""

  if (
    _gate_value(report) == 'blocked'
    or selected_launch_path == SessionLaunchPath.BLOCKED
    or _pit_hard_block(pit_inspection)
    or _pit_missing_required(
      session,
      pit_inspection,
      pit_required_for_safe_path,
    )
  ):
    return SafePathReadiness.BLOCKED
  if _fallback_active(session):
    return SafePathReadiness.NARROWED
  if session.live_detection.state in (
    LiveDetectionState.ATTENTION,
    LiveDetectionState.FAILED,
  ):
    return SafePathReadiness.NARROWED
  if session.inspection.posture in (
    InspectionWorkflowPosture.PARTIAL,
    InspectionWorkflowPosture.FAILED,
  ):
    return SafePathReadiness.NARROWED
  if _pit_narrows(pit_inspection):
    return SafePathReadiness.NARROWED
  if selected_launch_path == SessionLaunchPath.SAFE_PATH_CANDIDATE:
    return SafePathReadiness.READY
  return SafePathReadiness.UNREVIEWED


def _block_reason(
  session: PlatformSession,
  report: object,
  selected_launch_path: SessionLaunchPath,
  pit_inspection: Optional[object],
  pit_required_for_safe_path: bool,
) -> Optional[str]:
  """Return the most useful current block or narrowing reason."""

  if selected_launch_path == SessionLaunchPath.FALLBACK_REVIEW:
    return session.live_detection.fallback_reason
  pit_reason = _pit_alignment_reason(pit_inspection)
  if _pit_missing_required(session, pit_inspection, pit_required_for_safe_path):
    return 'Run Read PIT before continuing the bounded safe-path workflow.'
  if _pit_hard_block(pit_inspection):
    return pit_reason
  if _gate_value(report) == 'blocked':
    first_block_signal = _first_block_signal(report)
    if first_block_signal is not None:
      return first_block_signal.summary
    return getattr(report, 'recommended_action', None)
  if session.live_detection.state == LiveDetectionState.ATTENTION:
    return session.live_detection.summary
  if session.live_detection.state == LiveDetectionState.FAILED:
    return session.live_detection.summary
  if session.inspection.posture == InspectionWorkflowPosture.FAILED:
    return session.inspection.summary
  if pit_reason is not None and _pit_narrows(pit_inspection):
    return pit_reason
  return None


def _refresh_state(
  session: PlatformSession,
) -> Tuple[SessionRefreshState, Optional[str]]:
  """Return whether the session truth should be cleared or refreshed."""

  if (
    session.live_detection.state == LiveDetectionState.CLEARED
    and session.live_detection.source_labels
  ):
    return (
      SessionRefreshState.CLEAR_REQUIRED,
      'Latest live detection cleared the active path; clear stale live labels before continuing.',
    )
  if session.live_detection.state in (
    LiveDetectionState.ATTENTION,
    LiveDetectionState.FAILED,
  ):
    return (
      SessionRefreshState.REFRESH_RECOMMENDED,
      'Refresh live detection before trusting the current launch-state authority.',
    )
  if session.inspection.posture in (
    InspectionWorkflowPosture.PARTIAL,
    InspectionWorkflowPosture.FAILED,
  ):
    return (
      SessionRefreshState.REFRESH_RECOMMENDED,
      'Refresh the inspect-only workflow before treating the current session authority as stable.',
    )
  if session.phase == SessionPhase.RESUME_NEEDED:
    return (
      SessionRefreshState.REFRESH_RECOMMENDED,
      'Refresh session authority after the manual resume step completes.',
    )
  return SessionRefreshState.FRESH, None


def _summary(
  session: PlatformSession,
  selected_launch_path: SessionLaunchPath,
  ownership: SafePathOwnership,
  readiness: SafePathReadiness,
  block_reason: Optional[str],
  refresh_state: SessionRefreshState,
) -> str:
  """Return a compact human-readable session-authority summary."""

  if selected_launch_path == SessionLaunchPath.STANDBY:
    return (
      'Session authority is on standby: no selected launch path is active yet.'
    )
  if selected_launch_path == SessionLaunchPath.BLOCKED:
    return 'Session authority is blocked: {reason}'.format(
      reason=block_reason or 'blocking trust findings still need resolution.',
    )
  if selected_launch_path == SessionLaunchPath.FALLBACK_REVIEW:
    return 'Session authority is pinned to {path}: {reason}'.format(
      path=session.live_detection.path_identity.path_label,
      reason=block_reason or 'fallback handling is currently active.',
    )
  if selected_launch_path == SessionLaunchPath.SAFE_PATH_CANDIDATE:
    if readiness != SafePathReadiness.READY:
      return (
        'Session authority is pinned to a bounded safe-path candidate, but '
        'current readiness is narrowed while transport ownership remains {ownership}.'.format(
          ownership=ownership.value,
        )
      )
    return (
      'Session authority is pinned: reviewed truth is ready for a bounded '
      'safe-path candidate while transport ownership remains {ownership}.'.format(
        ownership=ownership.value,
      )
    )
  summary = (
    'Session authority is pinned to a review-only lane while reviewed, live, '
    'inspection, and fallback truth remain explicit.'
  )
  if ownership != SafePathOwnership.NATIVE:
    summary = (
      'Session authority is pinned to a review-only lane with {path} kept '
      'explicit while reviewed, live, inspection, and fallback truth remain '
      'separate.'.format(
        path=session.live_detection.path_identity.path_label,
      )
    )
  if readiness == SafePathReadiness.NARROWED:
    summary += ' Current readiness is narrowed pending refresh or clearer live-path truth.'
  if refresh_state == SessionRefreshState.CLEAR_REQUIRED:
    summary += ' Stale live surfaces must be cleared before the next path decision.'
  return summary


def _has_review_inputs(
  session: PlatformSession,
  package_assessment: Optional[object],
) -> bool:
  """Return whether reviewed session truth is materially hydrated."""

  return bool(
    session.guards.has_device
    or session.guards.package_loaded
    or package_assessment is not None
    or session.live_detection.state != LiveDetectionState.UNHYDRATED
    or session.last_event is not None
    or session.inspection.posture != InspectionWorkflowPosture.UNINSPECTED
  )


def _fallback_active(session: PlatformSession) -> bool:
  """Return whether fallback is currently visible in the session truth."""

  return session.live_detection.fallback_posture != LiveFallbackPosture.NOT_NEEDED


def _gate_value(report: object) -> str:
  """Return one preflight gate value from a loosely typed report."""

  gate = getattr(report, 'gate', None)
  if gate is None:
    return 'blocked'
  return getattr(gate, 'value', str(gate))


def _first_block_signal(report: object) -> Optional[object]:
  """Return the first blocking signal from a loosely typed preflight report."""

  for signal in getattr(report, 'signals', ()): 
    severity = getattr(signal, 'severity', None)
    severity_value = getattr(severity, 'value', str(severity))
    if severity_value == 'block':
      return signal
  return None


def _pit_hard_block(pit_inspection: Optional[object]) -> bool:
  """Return whether PIT truth independently blocks a safe-path claim."""

  pit_state = _pit_state_value(pit_inspection)
  if pit_state in ('failed', 'malformed'):
    return True
  if _pit_device_alignment_value(pit_inspection) == 'mismatched':
    return True
  return _pit_package_alignment_value(pit_inspection) == 'mismatched'


def _pit_missing_required(
  session: PlatformSession,
  pit_inspection: Optional[object],
  pit_required_for_safe_path: bool,
) -> bool:
  """Return whether the current bounded lane is still missing required PIT truth."""

  if not pit_required_for_safe_path or pit_inspection is not None:
    return False
  if session.phase in (
    SessionPhase.PACKAGE_LOADED,
    SessionPhase.VALIDATION_PASSED,
    SessionPhase.READY_TO_EXECUTE,
    SessionPhase.EXECUTING,
    SessionPhase.RESUME_NEEDED,
    SessionPhase.COMPLETED,
    SessionPhase.FAILED,
  ):
    return True
  snapshot = session.live_detection.snapshot
  if snapshot is None:
    return False
  return snapshot.source in (
    LiveDeviceSource.USB,
    LiveDeviceSource.HEIMDALL,
  ) and snapshot.command_ready


def _pit_narrows(pit_inspection: Optional[object]) -> bool:
  """Return whether PIT truth narrows but does not fully block readiness."""

  pit_state = _pit_state_value(pit_inspection)
  if pit_state == 'partial':
    return True
  if _pit_device_alignment_value(pit_inspection) == 'not_provided':
    return True
  return _pit_package_alignment_value(pit_inspection) in (
    'missing_reviewed',
    'missing_observed',
  )


def _pit_alignment_reason(pit_inspection: Optional[object]) -> Optional[str]:
  """Return one operator-facing PIT alignment reason when relevant."""

  pit_state = _pit_state_value(pit_inspection)
  if pit_state in ('failed', 'malformed'):
    return getattr(pit_inspection, 'summary', None)
  if _pit_device_alignment_value(pit_inspection) == 'mismatched':
    return 'Observed PIT product code does not match the current session device identity.'
  if _pit_package_alignment_value(pit_inspection) == 'mismatched':
    return 'Observed PIT fingerprint does not match the reviewed package fingerprint.'
  if pit_state == 'partial':
    return 'PIT review is still partial; metadata and partition rows do not yet fully agree.'
  if _pit_package_alignment_value(pit_inspection) == 'missing_reviewed':
    return 'Reviewed package truth does not yet provide a usable PIT fingerprint for comparison.'
  if _pit_package_alignment_value(pit_inspection) == 'missing_observed':
    return 'Observed PIT output did not provide a usable PIT fingerprint for comparison.'
  if _pit_device_alignment_value(pit_inspection) == 'not_provided':
    return 'Observed PIT truth did not provide a comparable product code for device alignment review.'
  return None


def _pit_state_value(pit_inspection: Optional[object]) -> Optional[str]:
  """Return one normalized PIT state value from a loosely typed inspection."""

  if pit_inspection is None:
    return None
  state = getattr(pit_inspection, 'state', None)
  if state is None:
    return None
  return getattr(state, 'value', str(state))


def _pit_package_alignment_value(pit_inspection: Optional[object]) -> Optional[str]:
  """Return one normalized PIT/package alignment value."""

  if pit_inspection is None:
    return None
  alignment = getattr(pit_inspection, 'package_alignment', None)
  if alignment is None:
    return None
  return getattr(alignment, 'value', str(alignment))


def _pit_device_alignment_value(pit_inspection: Optional[object]) -> Optional[str]:
  """Return one normalized PIT/device alignment value."""

  if pit_inspection is None:
    return None
  alignment = getattr(pit_inspection, 'device_alignment', None)
  if alignment is None:
    return None
  return getattr(alignment, 'value', str(alignment))

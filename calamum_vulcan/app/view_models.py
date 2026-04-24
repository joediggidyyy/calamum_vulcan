"""GUI-safe view models that bind the FS-03 shell to platform state."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from enum import Enum
from typing import Dict
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.domain.flash_plan import ReviewedFlashPlan
from calamum_vulcan.domain.flash_plan import build_reviewed_flash_plan
from calamum_vulcan.domain.live_device import LiveDetectionSession
from calamum_vulcan.domain.live_device import LiveDeviceInfoState
from calamum_vulcan.domain.live_device import LiveDetectionState
from calamum_vulcan.domain.live_device import LiveDeviceSnapshot
from calamum_vulcan.domain.live_device import LiveDeviceSource
from calamum_vulcan.domain.live_device import LiveDeviceSupportPosture
from calamum_vulcan.domain.package import PackageCompatibilityExpectation
from calamum_vulcan.domain.package import PackageManifestAssessment
from calamum_vulcan.domain.package import PackageRiskLevel
from calamum_vulcan.domain.pit import PitInspection
from calamum_vulcan.domain.pit import PitInspectionState
from calamum_vulcan.domain.preflight import PreflightGate
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import PreflightReport
from calamum_vulcan.domain.preflight import PreflightSeverity
from calamum_vulcan.domain.preflight import PreflightSignal
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.preflight import preflight_input_from_review_context
from calamum_vulcan.domain.reporting import SessionEvidenceReport
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import SessionAuthoritySnapshot
from calamum_vulcan.domain.state import SessionLaunchPath
from calamum_vulcan.domain.state import SessionPhase
from calamum_vulcan.domain.state import build_session_authority_snapshot


PANEL_TITLES = (
  'Device Identity',
  'Preflight Board',
  'Package Summary',
  'Transport State',
  'Session Evidence',
)

UNPOPULATED_VALUE = '--'

LIVE_PHASE_LABELS = {
  LiveDeviceSource.ADB: 'ADB Device Detected',
  LiveDeviceSource.FASTBOOT: 'Fastboot Device Detected',
  LiveDeviceSource.USB: 'Download-Mode Device Detected',
  LiveDeviceSource.HEIMDALL: 'Download-Mode Device Detected',
}  # type: Dict[LiveDeviceSource, str]

LIVE_PHASE_ATTENTION_LABELS = {
  LiveDeviceSource.ADB: 'ADB Device Attention',
  LiveDeviceSource.FASTBOOT: 'Fastboot Device Attention',
  LiveDeviceSource.USB: 'Download-Mode Device Attention',
  LiveDeviceSource.HEIMDALL: 'Download-Mode Device Attention',
}  # type: Dict[LiveDeviceSource, str]

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
}  # type: Dict[SessionPhase, str]

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
}  # type: Dict[SessionPhase, str]

GATE_LABELS = {
  PreflightGate.READY: 'Gate Ready',
  PreflightGate.WARN: 'Gate Warning',
  PreflightGate.BLOCKED: 'Gate Blocked',
}  # type: Dict[PreflightGate, str]

GATE_COMPACT_LABELS = {
  PreflightGate.READY: 'Ready',
  PreflightGate.WARN: 'Warn',
  PreflightGate.BLOCKED: 'Blocked',
}  # type: Dict[PreflightGate, str]

GATE_TONES = {
  PreflightGate.READY: 'success',
  PreflightGate.WARN: 'warning',
  PreflightGate.BLOCKED: 'danger',
}  # type: Dict[PreflightGate, str]


@dataclass(frozen=True)
class MetricViewModel:
  """A compact metric block rendered inside a dashboard panel."""

  label: str
  value: str
  tone: str = 'neutral'


@dataclass(frozen=True)
class StatusPillViewModel:
  """A compact status badge shown in the shell header."""

  label: str
  value: str
  tone: str = 'neutral'
  tooltip: Optional[str] = None


@dataclass(frozen=True)
class PanelViewModel:
  """Presentation contract for one dashboard card."""

  title: str
  eyebrow: str
  summary: str
  detail_lines: Tuple[str, ...] = ()
  metrics: Tuple[MetricViewModel, ...] = ()
  tone: str = 'neutral'


class ControlActionState(str, Enum):
  """Operator-visible workflow posture for one control-deck action."""

  HIDDEN = 'hidden'
  UNAVAILABLE = 'unavailable'
  AVAILABLE = 'available'
  NEXT = 'next'
  COMPLETED = 'completed'


class ControlActionSection(str, Enum):
  """Deck section used to separate the primary flow from contextual recovery."""

  PRIMARY = 'primary'
  CONTEXTUAL = 'contextual'


@dataclass(frozen=True)
class ControlActionViewModel:
  """A shell control-deck action with explicit workflow posture."""

  label: str
  hint: str
  state: ControlActionState
  enabled: bool
  emphasis: str = 'normal'
  section: ControlActionSection = ControlActionSection.PRIMARY

  @property
  def visible(self) -> bool:
    """Return whether the action should be rendered in the current deck."""

    return self.state != ControlActionState.HIDDEN


@dataclass(frozen=True)
class LiveCompanionDeviceViewModel:
  """Live companion metadata that can hydrate the main shell device surfaces."""

  backend: str
  serial: str
  state: str
  transport: str
  product_code: Optional[str] = None
  model_name: Optional[str] = None
  device_name: Optional[str] = None


@dataclass(frozen=True)
class ShellViewModel:
  """The full GUI shell description consumed by the Qt surface."""

  title: str
  subtitle: str
  scenario_name: str
  phase_label: str
  phase_tone: str
  gate_label: str
  gate_tone: str
  status_pills: Tuple[StatusPillViewModel, ...]
  panels: Tuple[PanelViewModel, ...]
  control_actions: Tuple[ControlActionViewModel, ...]
  log_lines: Tuple[str, ...]
  session_report: SessionEvidenceReport
  session_authority: SessionAuthoritySnapshot
  session: PlatformSession
  package_assessment: Optional[PackageManifestAssessment]
  pit_inspection: Optional[PitInspection]
  transport_trace: Optional[HeimdallNormalizedTrace]
  live_detection: LiveDetectionSession
  live_device: Optional[LiveCompanionDeviceViewModel] = None
  boot_unhydrated: bool = False
  device_surface_cleared: bool = False
  pit_required_for_safe_path: bool = False


def build_shell_view_model(
  session: PlatformSession,
  scenario_name: str = 'Live session',
  preflight_report: Optional[PreflightReport] = None,
  package_assessment: Optional[PackageManifestAssessment] = None,
  pit_inspection: Optional[PitInspection] = None,
  transport_trace: Optional[HeimdallNormalizedTrace] = None,
  session_report: Optional[SessionEvidenceReport] = None,
  live_detection: Optional[LiveDetectionSession] = None,
  live_device: Optional[LiveCompanionDeviceViewModel] = None,
  transport_backend: str = 'heimdall',
  boot_unhydrated: bool = False,
  device_surface_cleared: bool = False,
  pit_required_for_safe_path: bool = False,
) -> ShellViewModel:
  """Build the FS-03 shell model directly from the immutable session."""

  resolved_live_detection = _resolve_live_detection(
    session,
    live_detection,
    live_device,
  )
  resolved_device_surface_cleared = (
    device_surface_cleared
    or (
      resolved_live_detection.state == LiveDetectionState.CLEARED
      and resolved_live_detection.snapshot is None
    )
  )
  session = _session_with_live_detection(session, resolved_live_detection)
  report = preflight_report
  if report is None:
    report = _build_preflight_report(
      session,
      package_assessment,
      pit_inspection,
      pit_required_for_safe_path=pit_required_for_safe_path,
    )
  resolved_transport_backend = transport_backend
  if session_report is not None:
    resolved_transport_backend = session_report.flash_plan.transport_backend
  elif transport_trace is not None and getattr(transport_trace, 'adapter_name', 'heimdall') == 'integrated-runtime':
    resolved_transport_backend = 'integrated-runtime'
  evidence_report = session_report
  if evidence_report is None:
    evidence_report = build_session_evidence_report(
      session,
      scenario_name=scenario_name,
      preflight_report=report,
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      transport_trace=transport_trace,
      transport_backend=resolved_transport_backend,
      pit_required_for_safe_path=pit_required_for_safe_path,
    )
  authority = build_session_authority_snapshot(
    session,
    preflight_report=report,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  compatibility_live_device = _compat_live_device_overlay(resolved_live_detection)
  return ShellViewModel(
    title='Calamum Vulcan',
    subtitle=_build_shell_subtitle(authority, boot_unhydrated),
    scenario_name=scenario_name,
    phase_label=authority.live_phase_label,
    phase_tone=authority.live_phase_tone,
    gate_label='Standby' if boot_unhydrated else GATE_LABELS[report.gate],
    gate_tone='neutral' if boot_unhydrated else GATE_TONES[report.gate],
    status_pills=_build_status_pills(
      session,
      report,
      package_assessment,
      resolved_live_detection,
      authority,
      boot_unhydrated,
      resolved_device_surface_cleared,
    ),
    panels=_build_panels(
      session,
      report,
      package_assessment,
      pit_inspection,
      evidence_report,
      resolved_live_detection,
      authority,
      resolved_transport_backend,
      boot_unhydrated,
      resolved_device_surface_cleared,
    ),
    control_actions=_build_control_actions(
      session,
      report,
      evidence_report,
      pit_inspection,
      authority,
    ),
    log_lines=evidence_report.log_lines,
    session_report=evidence_report,
    session_authority=authority,
    session=session,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    transport_trace=transport_trace,
    live_detection=resolved_live_detection,
    live_device=compatibility_live_device,
    boot_unhydrated=boot_unhydrated,
    device_surface_cleared=resolved_device_surface_cleared,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )


def describe_shell(model: ShellViewModel) -> str:
  """Return a concise shell summary for evidence and CLI inspection."""

  panel_titles = ', '.join(panel.title for panel in model.panels)
  enabled_actions = ', '.join(
    action.label
    for action in model.control_actions
    if action.visible and action.enabled
  )
  if not enabled_actions:
    enabled_actions = 'none'
  return (
    'scenario={scenario} phase="{phase}" gate="{gate}" panels=[{panels}] '
    'enabled_actions=[{actions}]'.format(
      scenario=model.scenario_name,
      phase=model.phase_label,
      gate=model.gate_label,
      panels=panel_titles,
      actions=enabled_actions,
    )
  )


def _build_shell_subtitle(
  authority: SessionAuthoritySnapshot,
  boot_unhydrated: bool,
) -> str:
  """Return the current shell subtitle shown beneath the Vulcan wordmark."""

  return '{phase} · {context}'.format(
    phase=authority.live_phase_label,
    context=_shell_context_label(authority, boot_unhydrated),
  )


def _shell_context_label(
  authority: SessionAuthoritySnapshot,
  boot_unhydrated: bool,
) -> str:
  """Return the current header context label for the control deck."""

  if boot_unhydrated and authority.selected_launch_path == SessionLaunchPath.STANDBY:
    return 'startup standby shell'

  return {
    SessionLaunchPath.STANDBY: 'standby review shell',
    SessionLaunchPath.REVIEW_ONLY: 'review-only control deck',
    SessionLaunchPath.SAFE_PATH_CANDIDATE: 'safe-path candidate lane',
    SessionLaunchPath.FALLBACK_REVIEW: 'fallback review lane',
    SessionLaunchPath.BLOCKED: 'blocked review lane',
  }[authority.selected_launch_path]


def _resolve_live_detection(
  session: PlatformSession,
  live_detection: Optional[LiveDetectionSession],
  live_device: Optional[LiveCompanionDeviceViewModel],
) -> LiveDetectionSession:
  if live_detection is not None:
    return live_detection
  if live_device is not None:
    return _legacy_live_device_to_detection(live_device)
  return session.live_detection


def _session_with_live_detection(
  session: PlatformSession,
  live_detection: LiveDetectionSession,
) -> PlatformSession:
  if session.live_detection == live_detection:
    return session
  return replace(session, live_detection=live_detection)


def _compat_live_device_overlay(
  live_detection: LiveDetectionSession,
) -> Optional[LiveCompanionDeviceViewModel]:
  snapshot = live_detection.snapshot
  if snapshot is None:
    return None
  return LiveCompanionDeviceViewModel(
    backend=snapshot.source.value,
    serial=snapshot.serial,
    state=snapshot.connection_state,
    transport=snapshot.transport,
    product_code=snapshot.product_code,
    model_name=snapshot.model_name,
    device_name=snapshot.device_name,
  )


def _legacy_live_device_to_detection(
  live_device: LiveCompanionDeviceViewModel,
) -> LiveDetectionSession:
  source = LiveDeviceSource(live_device.backend)
  product_code = live_device.product_code or live_device.model_name
  device_resolution = resolve_device_profile(product_code)
  support_posture = LiveDeviceSupportPosture.IDENTITY_INCOMPLETE
  registry_match_kind = 'unknown'
  canonical_product_code = None
  marketing_name = None
  if product_code is not None:
    registry_match_kind = device_resolution.match_kind.value
    canonical_product_code = device_resolution.canonical_product_code
    marketing_name = device_resolution.marketing_name
    if device_resolution.known:
      support_posture = LiveDeviceSupportPosture.SUPPORTED
    else:
      support_posture = LiveDeviceSupportPosture.UNPROFILED

  snapshot = LiveDeviceSnapshot(
    source=source,
    serial=live_device.serial,
    connection_state=live_device.state,
    transport=live_device.transport,
    mode='{source}/{state}'.format(
      source=source.value,
      state=live_device.state,
    ),
    command_ready=(
      live_device.state == 'device'
      if source == LiveDeviceSource.ADB
      else live_device.state == 'fastboot'
      if source == LiveDeviceSource.FASTBOOT
      else live_device.state == 'download'
    ),
    product_code=product_code,
    model_name=live_device.model_name,
    device_name=live_device.device_name,
    canonical_product_code=canonical_product_code,
    marketing_name=marketing_name,
    registry_match_kind=registry_match_kind,
    support_posture=support_posture,
    info_state=(
      LiveDeviceInfoState.NOT_COLLECTED
      if source == LiveDeviceSource.ADB and live_device.state == 'device'
      else LiveDeviceInfoState.UNAVAILABLE
    ),
  )
  detection_state = LiveDetectionState.DETECTED
  if not snapshot.command_ready:
    detection_state = LiveDetectionState.ATTENTION
  return LiveDetectionSession(
    state=detection_state,
    summary='{backend} reported a live device through the compatibility overlay.'.format(
      backend=source.value.upper(),
    ),
    source=source,
    source_labels=(source.value,),
    snapshot=snapshot,
  )


def _build_status_pills(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  live_detection: LiveDetectionSession,
  authority: SessionAuthoritySnapshot,
  boot_unhydrated: bool,
  device_surface_cleared: bool,
) -> Tuple[StatusPillViewModel, ...]:
  live_snapshot = live_detection.snapshot
  phase_label = authority.live_phase_label
  phase_tone = authority.live_phase_tone
  phase_tooltip = authority.summary or 'Current reviewed-session phase.'
  gate_value = 'Standby' if boot_unhydrated else GATE_COMPACT_LABELS[report.gate]
  gate_tone = 'neutral' if boot_unhydrated else GATE_TONES[report.gate]
  gate_tooltip = _gate_pill_tooltip(report, boot_unhydrated)
  if boot_unhydrated:
    risk_value = UNPOPULATED_VALUE
    risk_tone = 'neutral'
    risk_tooltip = 'Risk stays blank until reviewed package truth is loaded.'
    device_value = UNPOPULATED_VALUE
    device_tone = 'neutral'
    device_tooltip = 'No live device probe has run yet.'
    package_value = UNPOPULATED_VALUE
    package_tone = 'neutral'
    package_tooltip = 'No reviewed package metadata is staged yet.'
  else:
    risk_value = _package_risk_value(session, package_assessment)
    risk_tone = 'neutral'
    if risk_value == 'destructive':
      risk_tone = 'danger'
    elif risk_value == 'standard':
      risk_tone = 'info'
    elif risk_value == 'advanced':
      risk_tone = 'warning'
    risk_tooltip = 'Current package risk tier: {risk}.'.format(
      risk=risk_value.upper(),
    )

    device_value = _device_pill_value(
      session,
      live_detection,
      device_surface_cleared,
    )
    device_tone = 'info' if session.guards.has_device or live_snapshot is not None else 'neutral'
    if device_surface_cleared and live_snapshot is None:
      device_tone = 'neutral'
    elif live_snapshot is not None and live_snapshot.command_ready:
      device_tone = 'success'
    elif live_snapshot is not None and not live_snapshot.command_ready:
      device_tone = 'warning'
    elif live_detection.state == LiveDetectionState.FAILED:
      device_tone = 'danger'
    device_tooltip = _device_pill_tooltip(
      session,
      live_detection,
      device_surface_cleared,
    )

    package_value = _package_label_value(session, package_assessment)
    package_tone = 'info' if session.guards.package_loaded else 'neutral'
    package_tooltip = _package_pill_tooltip(session, package_assessment)

  return (
    StatusPillViewModel(
      label='Phase',
      value=phase_label,
      tone=phase_tone,
      tooltip=phase_tooltip,
    ),
    StatusPillViewModel(
      label='Gate',
      value=gate_value,
      tone=gate_tone,
      tooltip=gate_tooltip,
    ),
    StatusPillViewModel(
      label='Device',
      value=device_value,
      tone=device_tone,
      tooltip=device_tooltip,
    ),
    StatusPillViewModel(
      label='Package',
      value=package_value,
      tone=package_tone,
      tooltip=package_tooltip,
    ),
    StatusPillViewModel(
      label='Risk',
      value=risk_value.upper(),
      tone=risk_tone,
      tooltip=risk_tooltip,
    ),
  )


def _gate_pill_tooltip(
  report: PreflightReport,
  boot_unhydrated: bool,
) -> str:
  """Return the hover detail for the compact Gate header pill."""

  if boot_unhydrated:
    return (
      'Standby — preflight has not evaluated the current session yet because '
      'device and package truth have not been hydrated.'
    )
  return (
    '{gate}: {summary} Passes={passes}, warnings={warnings}, blocks={blocks}.'.format(
      gate=GATE_LABELS[report.gate],
      summary=report.summary,
      passes=report.pass_count,
      warnings=report.warning_count,
      blocks=report.block_count,
    )
  )


def _device_pill_tooltip(
  session: PlatformSession,
  live_detection: LiveDetectionSession,
  device_surface_cleared: bool,
) -> str:
  """Return the hover detail for the Device header pill."""

  if device_surface_cleared and live_detection.snapshot is None:
    return 'Live device fields were cleared after the active device disconnected.'
  if live_detection.state == LiveDetectionState.UNHYDRATED:
    return 'No live device probe has run yet.'
  if live_detection.summary:
    return live_detection.summary
  return 'Current reviewed-session device state.'


def _package_pill_tooltip(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
) -> str:
  """Return the hover detail for the Package header pill."""

  if package_assessment is not None:
    return package_assessment.compatibility_summary
  if session.guards.package_loaded:
    return 'A package is staged, but reviewed manifest truth is still pending.'
  return 'No reviewed package metadata is currently loaded.'


def _build_panels(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  pit_inspection: Optional[PitInspection],
  session_report: SessionEvidenceReport,
  live_detection: LiveDetectionSession,
  authority: SessionAuthoritySnapshot,
  transport_backend: str,
  boot_unhydrated: bool,
  device_surface_cleared: bool,
) -> Tuple[PanelViewModel, ...]:
  return (
    _build_device_panel(
      session,
      live_detection,
      authority,
      boot_unhydrated,
      device_surface_cleared,
    ),
    _build_preflight_panel(session, report, boot_unhydrated),
    _build_package_panel(
      session,
      package_assessment,
      pit_inspection,
      transport_backend,
      boot_unhydrated,
    ),
    _build_transport_panel(
      session,
      session_report,
      authority,
      boot_unhydrated,
    ),
    _build_evidence_panel(session_report, authority, boot_unhydrated),
  )


def _display_phase(
  session: PlatformSession,
  live_detection: LiveDetectionSession,
) -> Tuple[str, str]:
  """Return the operator-facing phase label/tone for the current shell."""

  snapshot = live_detection.snapshot
  if (
    session.phase in (SessionPhase.NO_DEVICE, SessionPhase.DEVICE_DETECTED)
    and not session.guards.package_loaded
    and snapshot is not None
  ):
    if live_detection.state == LiveDetectionState.ATTENTION:
      return LIVE_PHASE_ATTENTION_LABELS[snapshot.source], 'warning'
    if snapshot.command_ready:
      return LIVE_PHASE_LABELS[snapshot.source], 'info'
    return LIVE_PHASE_ATTENTION_LABELS[snapshot.source], 'warning'
  return PHASE_LABELS[session.phase], PHASE_TONES[session.phase]


def _reviewed_target_phase_label(session: PlatformSession) -> str:
  """Return the explicit reviewed-target posture without live-phase overrides."""

  if session.phase == SessionPhase.NO_DEVICE:
    return 'No Download-Mode Target'
  return PHASE_LABELS[session.phase]


def _reviewed_target_posture_sentence(reviewed_target_phase: str) -> str:
  """Return one concise reviewed-target posture sentence for live summaries."""

  if reviewed_target_phase.startswith('Download-Mode Target'):
    return 'The reviewed target posture is now {phase}.'.format(
      phase=reviewed_target_phase,
    )
  return 'The reviewed target posture remains {phase}.'.format(
    phase=reviewed_target_phase,
  )


def _build_device_panel(
  session: PlatformSession,
  live_detection: LiveDetectionSession,
  authority: SessionAuthoritySnapshot,
  boot_unhydrated: bool,
  device_surface_cleared: bool,
) -> PanelViewModel:
  live_snapshot = live_detection.snapshot
  live_product_code = _live_product_code(live_snapshot)
  device_resolution = resolve_device_profile(live_product_code or session.product_code)

  if boot_unhydrated and live_snapshot is None:
    return PanelViewModel(
      title='Device Identity',
      eyebrow='DEVICE',
      summary=(
        'Device identity is intentionally blank at boot. Run a live companion '
        'probe or load a reviewed session to hydrate this surface.'
      ),
      detail_lines=(
        'Boot state: no live device probe has run yet.',
        'Reviewed session import: no device metadata is loaded.',
      ),
      metrics=(
        MetricViewModel('Presence', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Product code', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Registry', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Mode', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='neutral',
    )

  if device_surface_cleared and live_snapshot is None:
    next_action = _live_detection_next_action(
      live_detection,
      default='Reconnect and run Detect device again.',
    )
    details = [
      'Latest detect: {summary}'.format(summary=live_detection.summary),
      'Next action: {action}'.format(action=next_action),
    ]
    details.extend(_live_path_identity_lines(live_detection))
    details.extend(_live_fallback_lines(live_detection))
    return PanelViewModel(
      title='Device Identity',
      eyebrow='DEVICE',
      summary='No live device is currently detected.',
      detail_lines=tuple(details),
      metrics=(
        MetricViewModel('Presence', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Product code', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Registry', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Mode', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='neutral',
    )

  if live_detection.state == LiveDetectionState.FAILED and live_snapshot is None:
    next_action = _live_detection_next_action(
      live_detection,
      default='Verify adb/fastboot/native-usb availability and rerun Detect device.',
    )
    details = [
      'Latest detect: {summary}'.format(summary=live_detection.summary),
      'Next action: {action}'.format(action=next_action),
    ]
    details.extend(_live_path_identity_lines(live_detection))
    details.extend(_live_fallback_lines(live_detection))
    if _live_detection_self_heal_text(live_detection) is not None:
      details.append(
        'Self-heal: {command}'.format(
          command=_live_detection_self_heal_text(live_detection),
        )
      )
    for note in live_detection.notes[:2]:
      if note.startswith('Next step:'):
        continue
      details.append('Live note: {note}'.format(note=note))
    return PanelViewModel(
      title='Device Identity',
      eyebrow='DEVICE',
      summary='Live detection could not establish a trustworthy device identity.',
      detail_lines=tuple(details),
      metrics=(
        MetricViewModel('Presence', 'probe failed', 'danger'),
        MetricViewModel('Product code', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Registry', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Mode', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='danger',
    )

  if live_snapshot is not None:
    backend_label = live_snapshot.source.value.upper()
    reviewed_target_phase = authority.reviewed_target_label
    reviewed_target_sentence = _reviewed_target_posture_sentence(
      reviewed_target_phase
    )
    path_identity = live_detection.path_identity
    next_action = _live_detection_next_action(live_detection)
    if path_identity.ownership.value in ('delegated', 'fallback'):
      summary = '{path} identified {device} via {backend}. {sentence}'.format(
        path=path_identity.path_label,
        device=_live_device_summary_identity(live_snapshot, device_resolution),
        backend=backend_label,
        sentence=reviewed_target_sentence,
      )
    else:
      summary = 'Live companion detected {device} via {backend}. {sentence}'.format(
        device=_live_device_summary_identity(live_snapshot, device_resolution),
        backend=backend_label,
        sentence=reviewed_target_sentence,
      )
    if (
      not live_snapshot.command_ready
      or live_detection.state == LiveDetectionState.ATTENTION
    ):
      summary = 'Live companion identified {device} via {backend}, but it still needs operator attention. {sentence}'.format(
        device=_live_device_summary_identity(live_snapshot, device_resolution),
        backend=backend_label,
        sentence=reviewed_target_sentence,
      )
    elif live_snapshot.info_state == LiveDeviceInfoState.CAPTURED:
      summary = 'Live companion detected {device} via {backend}, and bounded read-side device info is now captured. {sentence}'.format(
        device=_live_device_summary_identity(live_snapshot, device_resolution),
        backend=backend_label,
        sentence=reviewed_target_sentence,
      )
    elif live_snapshot.info_state == LiveDeviceInfoState.PARTIAL:
      summary = 'Live companion detected {device} via {backend}, and a partial read-side info snapshot is available. {sentence}'.format(
        device=_live_device_summary_identity(live_snapshot, device_resolution),
        backend=backend_label,
        sentence=reviewed_target_sentence,
      )
    elif live_snapshot.info_state == LiveDeviceInfoState.FAILED:
      summary = 'Live companion detected {device} via {backend}, but richer read-side device info could not be captured. {sentence}'.format(
        device=_live_device_summary_identity(live_snapshot, device_resolution),
        backend=backend_label,
        sentence=reviewed_target_sentence,
      )
    details = [
      'Live serial: {serial}'.format(serial=live_snapshot.serial),
      'Live companion backend: {backend}'.format(backend=backend_label),
      'Live state: {state}'.format(state=live_snapshot.connection_state),
      'Live transport: {transport}'.format(transport=live_snapshot.transport),
      'Live mode: {mode}'.format(mode=live_snapshot.mode),
      'Reviewed target posture: {phase}'.format(phase=reviewed_target_phase),
    ]
    details.extend(_live_path_identity_lines(live_detection))
    details.extend(_live_fallback_lines(live_detection))
    if (
      next_action is not None
      and (
        live_detection.state == LiveDetectionState.ATTENTION
        or live_snapshot.support_posture == LiveDeviceSupportPosture.IDENTITY_INCOMPLETE
      )
    ):
      details.append('Primary next step: {action}'.format(action=next_action))
    if live_product_code is not None:
      details.append(
        'Live product code: {product_code}'.format(product_code=live_product_code)
      )
    if live_snapshot.model_name is not None and live_snapshot.model_name != live_product_code:
      details.append('Live model: {model}'.format(model=live_snapshot.model_name))
    if live_snapshot.device_name is not None:
      details.append(
        'Live device codename: {device}'.format(device=live_snapshot.device_name)
      )
    if session.mode is not None:
      details.append('Reviewed session mode: {mode}'.format(mode=session.mode))

    if live_snapshot.support_posture == LiveDeviceSupportPosture.SUPPORTED:
      details.append(
        'Marketing name: {name}'.format(
          name=live_snapshot.marketing_name or 'Samsung device',
        )
      )
      details.append(
        'Canonical product code: {product_code}'.format(
          product_code=(
            live_snapshot.canonical_product_code
            or live_product_code
            or 'unknown'
          ),
        )
      )
      details.append(
        'Registry match: {match}'.format(
          match=live_snapshot.registry_match_kind,
        )
      )
      if device_resolution.mode_entry_instructions:
        details.append(
          'Mode entry: {instruction}'.format(
            instruction=device_resolution.mode_entry_instructions[0],
          )
        )
      for quirk in device_resolution.known_quirks[:1]:
        details.append('Device quirk: {quirk}'.format(quirk=quirk))
      registry_value = live_snapshot.registry_match_kind
      registry_tone = 'success'
      if live_snapshot.registry_match_kind == DeviceRegistryMatchKind.ALIAS.value:
        registry_tone = 'info'
    elif live_snapshot.support_posture == LiveDeviceSupportPosture.UNPROFILED:
      details.extend(
        (
          'Support posture: unprofiled',
          'Add a repo-owned device profile before trusting compatibility resolution.',
        )
      )
      registry_value = 'unprofiled'
      registry_tone = 'warning'
    else:
      details.extend(
        (
          'Support posture: identity incomplete',
          'The active live source did not provide enough identity to resolve a repo-owned device profile.',
        )
      )
      registry_value = 'incomplete'
      registry_tone = 'warning'

    details.extend(_live_info_detail_lines(live_snapshot))

    for note in live_detection.notes[:2]:
      if note.startswith('Next step:') and next_action is not None:
        continue
      if note not in details:
        details.append('Live note: {note}'.format(note=note))

    tone = (
      'success'
      if live_snapshot.command_ready and live_detection.state != LiveDetectionState.ATTENTION
      else 'warning'
    )
    metrics = (
      MetricViewModel('Presence', 'live', tone),
      MetricViewModel('Product code', live_product_code or 'unknown', 'info'),
      MetricViewModel('Registry', registry_value, registry_tone),
      MetricViewModel('Mode', live_snapshot.mode, tone),
    )
    return PanelViewModel(
      title='Device Identity',
      eyebrow='DEVICE',
      summary=summary,
      detail_lines=tuple(details),
      metrics=metrics,
      tone=tone,
    )

  if session.guards.has_device:
    details = [
      'Mode: {mode}'.format(mode=session.mode or 'unknown'),
      'Device id: {device_id}'.format(
        device_id=session.device_id or 'pending registry lookup'
      ),
    ]
    if device_resolution.known:
      if device_resolution.match_kind == DeviceRegistryMatchKind.ALIAS:
        summary = '{detected} resolves to {canonical} ({name}) for shell review.'.format(
          detected=device_resolution.detected_product_code,
          canonical=device_resolution.canonical_product_code,
          name=device_resolution.marketing_name,
        )
      else:
        summary = '{product} resolved as {name} for shell review'.format(
          product=device_resolution.canonical_product_code or 'Samsung device',
          name=device_resolution.marketing_name or 'Samsung device',
        )
      details.append(
        'Marketing name: {name}'.format(
          name=device_resolution.marketing_name or 'Samsung device',
        )
      )
      details.append(
        'Canonical product code: {product_code}'.format(
          product_code=(
            device_resolution.canonical_product_code
            or device_resolution.detected_product_code
            or 'unknown'
          ),
        )
      )
      details.append(
        'Registry match: {match}'.format(
          match=device_resolution.match_kind.value,
        )
      )
      if device_resolution.mode_entry_instructions:
        details.append(
          'Mode entry: {instruction}'.format(
            instruction=device_resolution.mode_entry_instructions[0],
          )
        )
      for quirk in device_resolution.known_quirks[:1]:
        details.append('Device quirk: {quirk}'.format(quirk=quirk))
      tone = 'info'
      registry_value = device_resolution.match_kind.value
      registry_tone = 'success'
      if device_resolution.match_kind == DeviceRegistryMatchKind.ALIAS:
        registry_tone = 'info'
    else:
      summary = '{product} is not yet profiled in the device registry.'.format(
        product=device_resolution.detected_product_code or 'Detected device',
      )
      details.extend(
        (
          'Registry match: unknown',
          'Add a repo-owned device profile before trusting compatibility resolution.',
        )
      )
      tone = 'warning'
      registry_value = 'unknown'
      registry_tone = 'warning'
  else:
    summary = 'No Samsung download-mode device detected yet.'
    details = (
      'The GUI shell remains useful before hardware is attached.',
      'Fixture-driven layouts prevent backend pressure from leaking upward.',
    )
    tone = 'neutral'
    registry_value = 'pending'
    registry_tone = 'neutral'

  metrics = (
    MetricViewModel('Presence', 'present' if session.guards.has_device else 'none', tone),
    MetricViewModel('Product code', session.product_code or 'unknown', 'info'),
    MetricViewModel('Registry', registry_value, registry_tone),
    MetricViewModel('Mode', session.mode or 'idle', 'neutral'),
  )
  return PanelViewModel(
    title='Device Identity',
    eyebrow='DEVICE',
    summary=summary,
    detail_lines=tuple(details),
    metrics=metrics,
    tone=tone,
  )


def _device_pill_value(
  session: PlatformSession,
  live_detection: LiveDetectionSession,
  device_surface_cleared: bool,
) -> str:
  live_snapshot = live_detection.snapshot
  if device_surface_cleared and live_snapshot is None:
    return UNPOPULATED_VALUE
  if live_snapshot is None:
    if live_detection.state == LiveDetectionState.FAILED:
      return 'probe failed'
    return session.product_code or 'awaiting device'
  product_code = _live_product_code(live_snapshot)
  if product_code is not None:
    return '{product_code} via {backend}'.format(
      product_code=product_code,
      backend=live_snapshot.source.value.upper(),
    )
  return '{serial} via {backend}'.format(
    serial=live_snapshot.serial,
    backend=live_snapshot.source.value.upper(),
  )


def _live_product_code(
  live_snapshot: Optional[LiveDeviceSnapshot],
) -> Optional[str]:
  if live_snapshot is None:
    return None
  if live_snapshot.product_code is not None:
    return live_snapshot.product_code
  if live_snapshot.model_name is not None:
    return live_snapshot.model_name
  return None


def _live_device_summary_identity(
  live_snapshot: LiveDeviceSnapshot,
  device_resolution,
) -> str:
  if device_resolution.known:
    return '{name} ({product_code})'.format(
      name=device_resolution.marketing_name or 'Samsung device',
      product_code=(
        device_resolution.canonical_product_code
        or device_resolution.detected_product_code
        or live_snapshot.serial
      ),
    )
  live_product_code = _live_product_code(live_snapshot)
  if live_product_code is not None:
    return '{product_code} [{serial}]'.format(
      product_code=live_product_code,
      serial=live_snapshot.serial,
    )
  return live_snapshot.serial


def _live_fallback_lines(
  live_detection: LiveDetectionSession,
) -> Tuple[str, ...]:
  lines = []
  if live_detection.fallback_posture.value != 'not_needed':
    lines.append(
      'Fallback posture: {posture}'.format(
        posture=live_detection.fallback_posture.value.replace('_', ' '),
      )
    )
  if live_detection.source_labels:
    lines.append(
      'Sources considered: {sources}'.format(
        sources=' -> '.join(label.upper() for label in live_detection.source_labels),
      )
    )
  if live_detection.fallback_reason:
    lines.append(
      'Fallback reason: {reason}'.format(reason=live_detection.fallback_reason)
    )
  return tuple(lines)


def _live_path_identity_lines(
  live_detection: LiveDetectionSession,
) -> Tuple[str, ...]:
  """Return explicit delegated/fallback path-identity lines when relevant."""

  path_identity = live_detection.path_identity
  if path_identity.ownership.value in ('none', 'native'):
    return ()
  lines = [
    'Live path: {label}'.format(label=path_identity.path_label),
    'Delegated path label: {label}'.format(
      label=path_identity.delegated_path_label,
    ),
    'Path mode truth: {mode}'.format(mode=path_identity.mode_label),
    'Identity confidence: {confidence}'.format(
      confidence=path_identity.identity_confidence.value.replace('_', ' '),
    ),
    'Path summary: {summary}'.format(summary=path_identity.summary),
  ]
  for guidance in path_identity.operator_guidance[:1]:
    lines.append('Path guidance: {guidance}'.format(guidance=guidance))
  return tuple(lines)


def _live_info_detail_lines(
  live_snapshot: LiveDeviceSnapshot,
) -> Tuple[str, ...]:
  lines = [
    'Info posture: {posture}'.format(
      posture=live_snapshot.info_state.value.replace('_', ' '),
    )
  ]
  if live_snapshot.manufacturer is not None:
    lines.append('Manufacturer: {manufacturer}'.format(
      manufacturer=live_snapshot.manufacturer,
    ))
  if live_snapshot.brand is not None:
    lines.append('Brand: {brand}'.format(brand=live_snapshot.brand))
  if live_snapshot.android_version is not None:
    lines.append('Android version: {version}'.format(
      version=live_snapshot.android_version,
    ))
  if live_snapshot.security_patch is not None:
    lines.append('Security patch: {patch}'.format(
      patch=live_snapshot.security_patch,
    ))
  if live_snapshot.bootloader_version is not None:
    lines.append('Bootloader: {bootloader}'.format(
      bootloader=live_snapshot.bootloader_version,
    ))
  if live_snapshot.build_id is not None:
    lines.append('Build id: {build_id}'.format(build_id=live_snapshot.build_id))
  capability_hints = list(live_snapshot.capability_hints[:3])
  info_hint = next(
    (
      hint
      for hint in live_snapshot.capability_hints
      if hint.startswith('bounded_info_snapshot_')
    ),
    None,
  )
  if info_hint is not None and info_hint not in capability_hints:
    capability_hints.append(info_hint)
  for capability in capability_hints:
    lines.append('Capability hint: {hint}'.format(
      hint=capability.replace('_', ' '),
    ))
  for guidance in live_snapshot.operator_guidance[:2]:
    lines.append('Next step: {guidance}'.format(guidance=guidance))
  return tuple(lines)


def _build_preflight_panel(
  session: PlatformSession,
  report: PreflightReport,
  boot_unhydrated: bool,
) -> PanelViewModel:
  if boot_unhydrated:
    return PanelViewModel(
      title='Preflight Board',
      eyebrow='PREFLIGHT',
      summary='Preflight remains on standby until device and package review surfaces are hydrated.',
      detail_lines=(
        'Boot state: no trust inputs have been collected yet.',
        'Next action: detect a device or stage a reviewed package before expecting gate decisions.',
      ),
      metrics=(
        MetricViewModel('Gate', 'Standby', 'neutral'),
        MetricViewModel('Passes', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Warnings', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Blocks', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='neutral',
    )
  summary = report.summary
  tone = GATE_TONES[report.gate]
  notes = _preflight_detail_lines(report)
  metrics = (
    MetricViewModel(
      'Gate',
      GATE_COMPACT_LABELS[report.gate],
      GATE_TONES[report.gate],
    ),
    MetricViewModel(
      'Passes',
      str(report.pass_count),
      'success',
    ),
    MetricViewModel(
      'Warnings',
      str(report.warning_count),
      'warning' if report.warning_count else 'neutral',
    ),
    MetricViewModel(
      'Blocks',
      str(report.block_count),
      'danger' if report.block_count else 'neutral',
    ),
  )
  return PanelViewModel(
    title='Preflight Board',
    eyebrow='PREFLIGHT',
    summary=summary,
    detail_lines=tuple(notes),
    metrics=metrics,
    tone=tone,
  )


def _build_package_panel(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
  pit_inspection: Optional[PitInspection],
  transport_backend: str,
  boot_unhydrated: bool,
) -> PanelViewModel:
  if boot_unhydrated and package_assessment is None:
    return PanelViewModel(
      title='Package Summary',
      eyebrow='PACKAGE',
      summary=(
        'Package review surfaces stay blank at boot. Load a reviewed package to '
        'hydrate compatibility, flash-plan, and digest evidence.'
      ),
      detail_lines=(
        'Boot state: no package metadata is staged yet.',
        'Operational policy: compatibility and flash-plan fields remain empty until reviewed package truth is loaded.',
      ),
      metrics=(
        MetricViewModel('Loaded', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Risk', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Compatibility', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Plan', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='neutral',
    )
  if package_assessment is None:
    if session.guards.package_loaded:
      summary = '{package} is staged for review.'.format(
        package=session.package_id or 'Selected package'
      )
      tone = 'info'
      details = (
        'Risk level: {risk}'.format(
          risk=(session.package_risk or 'unclassified').upper()
        ),
        'Reviewed flash-plan surfaces arrive once a package assessment exists.',
        'Package truth is already treated as a first-class operator surface.',
      )
    else:
      summary = 'No firmware package is currently loaded.'
      tone = 'neutral'
      details = (
        'The shell still reserves package territory before parsing exists.',
        'Compatibility routing remains fixture-driven in this stack.',
      )

    metrics = (
      MetricViewModel(
        'Loaded',
        'yes' if session.guards.package_loaded else 'no',
        'info' if session.guards.package_loaded else 'neutral',
      ),
      MetricViewModel('Package id', session.package_id or 'none', 'info'),
      MetricViewModel(
        'Risk',
        (session.package_risk or 'none').upper(),
        'danger' if session.package_risk == 'destructive' else 'info',
      ),
    )
    return PanelViewModel(
      title='Package Summary',
      eyebrow='PACKAGE',
      summary=summary,
      detail_lines=details,
      metrics=metrics,
      tone=tone,
    )

  summary = '{name} v{version} is staged for package-aware review.'.format(
    name=package_assessment.display_name,
    version=package_assessment.version,
  )
  reviewed_flash_plan = build_reviewed_flash_plan(
    package_assessment,
    transport_backend=transport_backend,
  )
  tone = _package_panel_tone(package_assessment)
  if package_assessment.contract_issues:
    summary = '{name} manifest needs correction before a trusted flash plan can exist.'.format(
      name=package_assessment.display_name,
    )
  elif package_assessment.analyzed_snapshot_drift_detected:
    summary = '{name} no longer matches the sealed analyzed snapshot.'.format(
      name=package_assessment.display_name,
    )
  elif package_assessment.snapshot_issues:
    summary = '{name} still needs a verified analyzed snapshot before execution can proceed.'.format(
      name=package_assessment.display_name,
    )
  elif (
    session.guards.has_device
    and not package_assessment.matches_detected_product_code
  ):
    if (
      package_assessment.detected_product_code is not None
      and not package_assessment.device_registry_known
    ):
      summary = '{name} cannot be cleared because {product} is not yet in the device registry.'.format(
        name=package_assessment.display_name,
        product=package_assessment.detected_product_code,
      )
    elif (
      package_assessment.resolved_device_name is not None
      and package_assessment.resolved_product_code is not None
    ):
      summary = '{name} does not match {device} ({product}).'.format(
        name=package_assessment.display_name,
        device=package_assessment.resolved_device_name,
        product=package_assessment.resolved_product_code,
      )
    else:
      summary = '{name} does not match the detected Samsung product code.'.format(
        name=package_assessment.display_name,
      )
  elif pit_inspection is not None and pit_inspection.device_alignment.value == 'mismatched':
    summary = '{name} cannot be cleared because the observed device PIT does not match the current session device identity.'.format(
      name=package_assessment.display_name,
    )
    tone = 'danger'
  elif pit_inspection is not None and pit_inspection.package_alignment.value == 'mismatched':
    summary = '{name} does not match the observed device PIT fingerprint.'.format(
      name=package_assessment.display_name,
    )
    tone = 'danger'
  elif pit_inspection is not None and pit_inspection.state in (
    PitInspectionState.MALFORMED,
    PitInspectionState.FAILED,
  ):
    summary = '{name} still needs trustworthy PIT inspection truth before deeper review should continue.'.format(
      name=package_assessment.display_name,
    )
    tone = 'warning'
  elif pit_inspection is not None and pit_inspection.state == PitInspectionState.PARTIAL:
    summary = '{name} still needs complete PIT alignment truth before the current safe-path claim should widen.'.format(
      name=package_assessment.display_name,
    )
    tone = 'warning'
  elif pit_inspection is not None and pit_inspection.package_alignment.value in (
    'missing_reviewed',
    'missing_observed',
  ):
    summary = '{name} still needs a complete PIT fingerprint comparison before the current safe-path claim should widen.'.format(
      name=package_assessment.display_name,
    )
    tone = 'warning'
  elif pit_inspection is not None and pit_inspection.device_alignment.value == 'not_provided':
    summary = '{name} still needs PIT/device alignment truth before the current safe-path claim should widen.'.format(
      name=package_assessment.display_name,
    )
    tone = 'warning'
  elif not reviewed_flash_plan.ready_for_transport:
    summary = reviewed_flash_plan.summary
  elif package_assessment.suspicious_warning_count:
    summary = '{name} is structurally usable but carries warning-tier suspicious Android traits that remain visible for operator review.'.format(
      name=package_assessment.display_name,
    )

  metrics = (
    MetricViewModel('Loaded', 'yes', 'info'),
    MetricViewModel(
      'Compatibility',
      package_assessment.compatibility_expectation.value.upper(),
      'danger'
      if package_assessment.compatibility_expectation == PackageCompatibilityExpectation.MISMATCH
      else 'warning'
      if package_assessment.compatibility_expectation == PackageCompatibilityExpectation.INCOMPLETE
      else 'success',
    ),
    MetricViewModel(
      'Risk',
      _package_risk_value(session, package_assessment).upper(),
      _risk_tone(package_assessment.risk_level),
    ),
    MetricViewModel(
      'Plan',
      '{partitions} partitions / {checksums} checksums'.format(
        partitions=len(package_assessment.partitions),
        checksums=len(package_assessment.checksums),
      ),
      'info',
    ),
  )
  return PanelViewModel(
    title='Package Summary',
    eyebrow='PACKAGE',
    summary=summary,
    detail_lines=_package_detail_lines(
      package_assessment,
      reviewed_flash_plan,
      pit_inspection,
    ),
    metrics=metrics,
    tone=tone,
  )


def _build_transport_panel(
  session: PlatformSession,
  session_report: SessionEvidenceReport,
  authority: SessionAuthoritySnapshot,
  boot_unhydrated: bool,
) -> PanelViewModel:
  phase_label = authority.live_phase_label
  phase_tone = authority.live_phase_tone
  if boot_unhydrated:
    return PanelViewModel(
      title='Transport State',
      eyebrow='TRANSPORT',
      summary='Transport is idle at boot. No reviewed flash plan has generated a command path yet.',
      detail_lines=(
        'Boot state: no transport command has been prepared or executed.',
        'Next action: hydrate device and package surfaces before transport review begins.',
      ),
      metrics=(
        MetricViewModel('Phase', phase_label, phase_tone),
        MetricViewModel('Transport', 'standby', 'neutral'),
        MetricViewModel('Exit code', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Mode', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='neutral',
    )
  transport = session_report.transport
  tone = _transport_tone(transport.state)
  details = [
    'Launch path: {path}'.format(
      path=authority.selected_launch_path_label,
    ),
    'Path ownership: {ownership}'.format(
      ownership=authority.ownership.value.replace('_', ' '),
    ),
    'Authority readiness: {readiness}'.format(
      readiness=authority.readiness.value.replace('_', ' '),
    ),
    'Adapter: {adapter}'.format(adapter=transport.adapter_name),
    'Capability: {capability}'.format(capability=transport.capability),
    'Command: {command}'.format(command=transport.command_display),
    'Normalized events: {count}'.format(count=transport.normalized_event_count),
  ]
  details.extend(_safe_path_governance_lines(session_report))
  live_path_identity = session_report.device.live.path_identity
  if live_path_identity.ownership in ('delegated', 'fallback'):
    details.extend(
      (
        'Live path identity: {label}'.format(
          label=live_path_identity.path_label,
        ),
        'Delegated label: {label}'.format(
          label=live_path_identity.delegated_path_label,
        ),
        'Path confidence: {confidence}'.format(
          confidence=live_path_identity.identity_confidence.replace('_', ' '),
        ),
      )
    )
  if authority.block_reason is not None:
    details.append('Authority block reason: {reason}'.format(
      reason=authority.block_reason,
    ))
  if authority.refresh_reason is not None:
    details.append('Authority refresh: {reason}'.format(
      reason=authority.refresh_reason,
    ))
  if transport.progress_markers:
    details.append(
      'Progress markers: {markers}'.format(
        markers=', '.join(transport.progress_markers),
      )
    )
  for note in transport.notes[:2]:
    details.append('Transport note: {note}'.format(note=note))
  if session.failure_reason:
    details.append('Failure: {reason}'.format(reason=session.failure_reason))

  metrics = (
    MetricViewModel('Phase', phase_label, phase_tone),
    MetricViewModel(
      'Transport',
      transport.state.replace('_', ' '),
      tone,
    ),
    MetricViewModel(
      'Exit code',
      str(transport.exit_code) if transport.exit_code is not None else 'n/a',
      'danger' if transport.exit_code not in (None, 0) else 'info',
    ),
    MetricViewModel('Mode', session.mode or 'idle', 'neutral'),
  )
  return PanelViewModel(
    title='Transport State',
    eyebrow='TRANSPORT',
    summary=transport.summary,
    detail_lines=tuple(details),
    metrics=metrics,
    tone=tone,
  )


def _build_evidence_panel(
  session_report: SessionEvidenceReport,
  authority: SessionAuthoritySnapshot,
  boot_unhydrated: bool,
) -> PanelViewModel:
  if boot_unhydrated:
    return PanelViewModel(
      title='Session Evidence',
      eyebrow='EVIDENCE',
      summary='Evidence export is initialized but intentionally sparse until operator actions hydrate the session.',
      detail_lines=(
        'Boot state: no operator actions or transport receipts have been recorded yet.',
        'Export policy: structured evidence becomes meaningful after reviewed inputs or live actions occur.',
      ),
      metrics=(
        MetricViewModel('Trace', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Logs', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Outcome', 'standby', 'neutral'),
        MetricViewModel('Exports', 'pending', 'neutral'),
      ),
      tone='neutral',
    )
  tone = _evidence_tone(session_report)
  details = [
    'Report id: {report_id}'.format(
      report_id=session_report.report_id,
    ),
    'Captured at: {captured}'.format(
      captured=session_report.captured_at_utc,
    ),
    'Authority summary: {summary}'.format(
      summary=authority.summary,
    ),
    'Launch path: {path} / {ownership} / {readiness}'.format(
      path=authority.selected_launch_path_label,
      ownership=authority.ownership.value,
      readiness=authority.readiness.value,
    ),
    'Live path identity: {path} / {ownership} / {confidence}'.format(
      path=session_report.device.live.path_identity.path_label,
      ownership=session_report.device.live.path_identity.ownership,
      confidence=session_report.device.live.path_identity.identity_confidence,
    ),
    'Flash plan id: {plan_id}'.format(
      plan_id=session_report.flash_plan.plan_id,
    ),
    'Flash plan posture: {posture}'.format(
      posture=(
        'ready for transport review'
        if session_report.flash_plan.ready_for_transport
        else 'blocked pending trust review'
      )
    ),
    'Flash plan summary: {summary}'.format(
      summary=session_report.flash_plan.summary,
    ),
    'Suspicious traits: {count} ({summary})'.format(
      count=session_report.package.suspicious_warning_count,
      summary=session_report.package.suspiciousness_summary,
    ),
    'PIT posture: {state} / {alignment}'.format(
      state=session_report.pit.state,
      alignment=session_report.pit.package_alignment,
    ),
    'PIT/device alignment: {alignment}'.format(
      alignment=session_report.pit.device_alignment,
    ),
    'Observed PIT fingerprint: {fingerprint}'.format(
      fingerprint=session_report.pit.observed_pit_fingerprint or 'unknown',
    ),
    'Recommended action: {action}'.format(
      action=session_report.preflight.recommended_action,
    ),
    'Recovery guidance: {guidance}'.format(
      guidance=session_report.outcome.recovery_guidance[0],
    ),
    'Export targets: {targets}'.format(
      targets=', '.join(target.upper() for target in session_report.host.export_targets),
    ),
  ]
  details.extend(_safe_path_governance_lines(session_report))
  if session_report.device.live.path_identity.ownership in ('delegated', 'fallback'):
    details.append(
      'Live delegated label: {label}'.format(
        label=session_report.device.live.path_identity.delegated_path_label,
      )
    )
    details.append(
      'Live path summary: {summary}'.format(
        summary=session_report.device.live.path_identity.summary,
      )
    )
    if session_report.device.live.path_identity.operator_guidance:
      details.append(
        'Live path guidance: {guidance}'.format(
          guidance=session_report.device.live.path_identity.operator_guidance[0],
        )
      )
  if authority.block_reason is not None:
    details.append('Authority block reason: {reason}'.format(
      reason=authority.block_reason,
    ))
  if authority.refresh_reason is not None:
    details.append('Authority refresh: {reason}'.format(
      reason=authority.refresh_reason,
    ))
  if session_report.inspection.posture != 'uninspected':
    details.extend(
      (
        'Inspection posture: {posture}'.format(
          posture=session_report.inspection.posture,
        ),
        'Inspection summary: {summary}'.format(
          summary=session_report.inspection.summary,
        ),
        'Inspection next action: {action}'.format(
          action=session_report.inspection.next_action,
        ),
      )
    )
    for boundary in session_report.inspection.action_boundaries[:1]:
      details.append('Inspection boundary: {boundary}'.format(
        boundary=boundary,
      ))
    for note in session_report.inspection.notes[:1]:
      details.append('Inspection note: {note}'.format(note=note))
  if session_report.package.snapshot_id is not None:
    details.append(
      'Analyzed snapshot: {snapshot_id}'.format(
        snapshot_id=session_report.package.snapshot_id,
      )
    )
    details.append(
      'Snapshot verification: {verified}'.format(
        verified='verified'
        if session_report.package.snapshot_verified
        else 'blocked',
      )
    )
  for requirement in session_report.flash_plan.advanced_requirements[:1]:
    details.append('Advanced requirement: {requirement}'.format(
      requirement=requirement,
    ))
  if session_report.pit.partition_names:
    details.append(
      'Observed PIT partitions: {partitions}'.format(
        partitions=', '.join(session_report.pit.partition_names),
      )
    )
  if session_report.pit.download_path:
    details.append(
      'Downloaded PIT artifact: {path}'.format(
        path=session_report.pit.download_path,
      )
    )
  for guidance in session_report.pit.operator_guidance[:1]:
    details.append('PIT guidance: {guidance}'.format(guidance=guidance))
  for warning in session_report.flash_plan.operator_warnings[:1]:
    details.append('Flash plan warning: {warning}'.format(warning=warning))
  for blocker in session_report.flash_plan.blocking_reasons[:1]:
    details.append('Flash plan blocker: {blocker}'.format(blocker=blocker))
  for trace in session_report.decision_trace[:2]:
    details.append(
      'Decision trace: {label} -> {summary}'.format(
        label=trace.label,
        summary=trace.summary,
      )
    )

  metrics = (
    MetricViewModel('Trace', str(len(session_report.decision_trace)), 'info'),
    MetricViewModel('Logs', str(len(session_report.log_lines)), 'info'),
    MetricViewModel(
      'Outcome',
      session_report.outcome.outcome.replace('_', ' '),
      tone,
    ),
    MetricViewModel(
      'Exports',
      ' / '.join(target.upper() for target in session_report.host.export_targets),
      'success' if session_report.outcome.export_ready else 'neutral',
    ),
  )
  return PanelViewModel(
    title='Session Evidence',
    eyebrow='EVIDENCE',
    summary=session_report.summary,
    detail_lines=tuple(details),
    metrics=metrics,
    tone=tone,
  )


def _build_control_actions(
  session: PlatformSession,
  report: PreflightReport,
  session_report: SessionEvidenceReport,
  pit_inspection: Optional[PitInspection],
  authority: SessionAuthoritySnapshot,
) -> Tuple[ControlActionViewModel, ...]:
  live_detection = session.live_detection
  detect_completed = _detect_action_complete(live_detection)
  download_mode_snapshot = _download_mode_snapshot(session)
  pit_capture_complete = _pit_capture_complete(session_report)
  read_pit_state = ControlActionState.UNAVAILABLE
  read_pit_enabled = False
  read_pit_hint = (
    'Read PIT unlocks only after Detect device finds an active Samsung download-mode session through the native USB lane.'
  )
  read_pit_emphasis = 'normal'
  if pit_capture_complete:
    read_pit_state = ControlActionState.COMPLETED
    read_pit_hint = (
      'Re-read bounded PIT truth for the current Samsung download-mode session.'
    )
  elif download_mode_snapshot is not None:
    read_pit_enabled = True
    if pit_inspection is not None and pit_inspection.state in (
      PitInspectionState.FAILED,
      PitInspectionState.MALFORMED,
    ):
      read_pit_state = ControlActionState.NEXT
      read_pit_hint = (
        'The last PIT read did not capture trustworthy partition truth. Review the PIT failure details, then retry Read PIT.'
      )
      read_pit_emphasis = 'next_danger'
    elif pit_inspection is not None and pit_inspection.state == PitInspectionState.PARTIAL:
      read_pit_state = ControlActionState.NEXT
      read_pit_hint = (
        'The last PIT read captured only partial partition truth. Retry Read PIT to complete the bounded PIT review.'
      )
      read_pit_emphasis = 'next_warning'
    else:
      read_pit_state = ControlActionState.NEXT
      read_pit_hint = (
        'Capture bounded PIT truth from the current Samsung download-mode session.'
      )
      read_pit_emphasis = 'next'
  package_loaded = bool(
    session.guards.package_loaded
    or session_report.package.source_kind != 'pending'
  )
  flash_attempted = session_report.transport.state in (
    'executing',
    'resume_needed',
    'completed',
    'failed',
  )
  execution_resolved = session_report.transport.state in ('completed', 'failed')
  execute_ready = bool(
    authority.selected_launch_path == SessionLaunchPath.SAFE_PATH_CANDIDATE
    and authority.readiness.value == 'ready'
    and report.ready_for_execution
    and session_report.flash_plan.ready_for_transport
  )
  execute_state = ControlActionState.UNAVAILABLE
  if flash_attempted:
    execute_state = ControlActionState.COMPLETED
  elif execute_ready:
    execute_state = ControlActionState.NEXT
  elif package_loaded and pit_capture_complete and session_report.flash_plan.ready_for_transport:
    execute_state = ControlActionState.AVAILABLE

  execute_emphasis = 'normal'
  if execute_state == ControlActionState.NEXT:
    execute_emphasis = 'next'
    if session.package_risk == 'destructive':
      execute_emphasis = 'next_danger'
  elif execute_state == ControlActionState.AVAILABLE:
    execute_emphasis = 'primary'
    if session.package_risk == 'destructive':
      execute_emphasis = 'danger'

  export_state = ControlActionState.UNAVAILABLE
  if session_report.outcome.export_ready:
    export_state = ControlActionState.NEXT if execution_resolved else ControlActionState.AVAILABLE

  resume_needed = bool(
    session.phase == SessionPhase.RESUME_NEEDED
    or session_report.transport.state == 'resume_needed'
  )
  return (
    ControlActionViewModel(
      label='Detect device',
      hint=_detect_action_hint(live_detection),
      state=(
        ControlActionState.COMPLETED
        if detect_completed
        else ControlActionState.NEXT
      ),
      enabled=True,
      emphasis=_detect_action_emphasis(live_detection, report),
    ),
    ControlActionViewModel(
      label='Read PIT',
      hint=read_pit_hint,
      state=read_pit_state,
      enabled=read_pit_enabled,
      emphasis=read_pit_emphasis,
    ),
    ControlActionViewModel(
      label='Load package',
      hint=(
        'Reviewed package truth is already staged; load a different firmware set only if the current review changes.'
        if package_loaded
        else 'Stage reviewed firmware metadata after PIT truth is captured.'
        if pit_capture_complete
        else 'Load package stays pinned behind Detect device and Read PIT in the Sprint 0.4.0 deck.'
      ),
      state=(
        ControlActionState.COMPLETED
        if package_loaded
        else ControlActionState.NEXT
        if pit_capture_complete
        else ControlActionState.UNAVAILABLE
      ),
      enabled=package_loaded or pit_capture_complete,
      emphasis='next' if not package_loaded and pit_capture_complete else 'normal',
    ),
    ControlActionViewModel(
      label='Execute flash plan',
      hint=(
        'The bounded safe-path lane already ran for this review state; export the resulting evidence bundle next.'
        if flash_attempted
        else 'Review-only placeholder until matched package, PIT, and preflight truth open the bounded safe-path lane.'
        if execute_state == ControlActionState.UNAVAILABLE
        else 'Review the bounded safe-path lane before handing control to the delegated lower transport.'
      ),
      state=execute_state,
      enabled=execute_ready,
      emphasis=execute_emphasis,
    ),
    ControlActionViewModel(
      label='Export evidence',
      hint=(
        'Export the resolved evidence bundle and preserved transcript artifacts.'
        if export_state == ControlActionState.NEXT
        else 'Export the current evidence bundle at any time without widening the write path.'
        if export_state == ControlActionState.AVAILABLE
        else 'Export becomes available after meaningful detection, review, or runtime activity.'
      ),
      state=export_state,
      enabled=session_report.outcome.export_ready,
      emphasis='next' if export_state == ControlActionState.NEXT else 'normal',
    ),
    ControlActionViewModel(
      label='Continue after recovery',
      hint='Complete the recorded manual recovery step, then resume the bounded safe-path workflow without pretending it is a normal deck stage.',
      state=(
        ControlActionState.NEXT
        if resume_needed
        else ControlActionState.HIDDEN
      ),
      enabled=resume_needed,
      emphasis='warning',
      section=ControlActionSection.CONTEXTUAL,
    ),
  )


def _detect_action_complete(
  live_detection: LiveDetectionSession,
) -> bool:
  """Return whether Detect device has completed honestly for the current deck."""

  snapshot = live_detection.snapshot
  if snapshot is None:
    return False
  if live_detection.state in (
    LiveDetectionState.ATTENTION,
    LiveDetectionState.FAILED,
  ):
    return False
  return snapshot.command_ready


def _live_detection_note_suffix(
  live_detection: LiveDetectionSession,
  prefix: str,
) -> Optional[str]:
  """Return the suffix for the first live note that matches one prefix."""

  for note in live_detection.notes:
    if not note.startswith(prefix):
      continue
    return note[len(prefix):].strip()
  return None


def _live_detection_self_heal_text(
  live_detection: LiveDetectionSession,
) -> Optional[str]:
  """Return one remediation command or helper note when the detect flow has one."""

  return _live_detection_note_suffix(
    live_detection,
    'Self-heal attempted:',
  )


def _live_detection_next_action(
  live_detection: LiveDetectionSession,
  default: Optional[str] = None,
) -> Optional[str]:
  """Return the best concrete next step currently attached to live detection."""

  next_action = _live_detection_note_suffix(live_detection, 'Next step:')
  if next_action is not None:
    return next_action
  if live_detection.path_identity.operator_guidance:
    return live_detection.path_identity.operator_guidance[0]
  return default


def _detect_action_hint(
  live_detection: LiveDetectionSession,
) -> str:
  """Return the current tooltip copy for the Detect device control."""

  next_action = _live_detection_next_action(live_detection)
  self_heal = _live_detection_self_heal_text(live_detection)
  if live_detection.state == LiveDetectionState.ATTENTION:
    parts = [
      'The last detect pass found a live device that is not yet command-ready.',
    ]
    if self_heal is not None:
      parts.append('Self-heal attempted: {command}.'.format(command=self_heal))
    if next_action is not None:
      parts.append('Next step: {action}'.format(action=next_action))
    else:
      parts.append('Resolve the attention condition, then rerun Detect device.')
    return ' '.join(parts)
  if live_detection.state == LiveDetectionState.FAILED:
    parts = [
      'The last detect pass did not produce trustworthy device truth.',
    ]
    if self_heal is not None:
      parts.append('Self-heal attempted: {command}.'.format(command=self_heal))
    if next_action is not None:
      parts.append('Next step: {action}'.format(action=next_action))
    else:
      parts.append(
        'Correct the blocking condition, then rerun Detect device.'
      )
    return ' '.join(parts)
  if live_detection.state == LiveDetectionState.CLEARED:
    if next_action is not None:
      return 'No live device is currently detected. Next step: {action}'.format(
        action=next_action,
      )
    return 'No live device is currently detected. Reconnect the device, then rerun Detect device.'
  if _detect_action_complete(live_detection):
    return 'Refresh unified live truth across ADB, fastboot, and Samsung download mode.'
  return 'Probe Samsung live presence and identity across ADB, fastboot, and the native USB download-mode lane.'


def _detect_action_emphasis(
  live_detection: LiveDetectionSession,
  report: PreflightReport,
) -> str:
  """Return the deck emphasis for the Detect device control."""

  if _detect_action_complete(live_detection):
    return 'normal'
  if live_detection.state in (
    LiveDetectionState.ATTENTION,
    LiveDetectionState.FAILED,
  ):
    return _severity_next_emphasis(report.gate)
  return 'next'


def _severity_next_emphasis(gate: PreflightGate) -> str:
  """Return the green-next emphasis variant that matches gate severity."""

  if gate == PreflightGate.BLOCKED:
    return 'next_danger'
  if gate == PreflightGate.WARN:
    return 'next_warning'
  return 'next'


def _download_mode_snapshot(
  session: PlatformSession,
) -> Optional[LiveDeviceSnapshot]:
  """Return the active download-mode snapshot when one is present."""

  snapshot = session.live_detection.snapshot
  if snapshot is None:
    return None
  if snapshot.source not in (LiveDeviceSource.USB, LiveDeviceSource.HEIMDALL):
    return None
  if not snapshot.command_ready:
    return None
  return snapshot


def _pit_capture_complete(
  session_report: SessionEvidenceReport,
) -> bool:
  """Return whether PIT truth is complete enough to unlock the next deck step."""

  return bool(
    session_report.pit.state == 'captured'
    and session_report.pit.device_alignment != 'not_provided'
  )


def _build_preflight_report(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
  pit_inspection: Optional[PitInspection],
  pit_required_for_safe_path: bool = False,
) -> PreflightReport:
  return evaluate_preflight(
    preflight_input_from_review_context(
      session,
      package_assessment=package_assessment,
      pit_inspection=pit_inspection,
      pit_required=pit_required_for_safe_path,
    )
  )


def _package_risk_value(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
) -> str:
  if package_assessment is not None and package_assessment.risk_level is not None:
    return package_assessment.risk_level.value
  return session.package_risk or 'unclassified'


def _package_label_value(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
) -> str:
  if package_assessment is not None:
    return package_assessment.display_package_id
  return session.package_id or 'awaiting package'


def _package_panel_tone(
  package_assessment: PackageManifestAssessment,
) -> str:
  if package_assessment.contract_issues:
    return 'danger'
  if package_assessment.analyzed_snapshot_drift_detected:
    return 'danger'
  if package_assessment.snapshot_issues:
    return 'warning'
  if package_assessment.suspicious_warning_count:
    return 'warning'
  if (
    package_assessment.detected_product_code is not None
    and not package_assessment.device_registry_known
  ):
    return 'danger'
  if package_assessment.compatibility_expectation == PackageCompatibilityExpectation.MISMATCH:
    return 'danger'
  if package_assessment.risk_level == PackageRiskLevel.DESTRUCTIVE:
    return 'warning'
  if package_assessment.risk_level == PackageRiskLevel.ADVANCED:
    return 'warning'
  return 'info'


def _risk_tone(risk_level: Optional[PackageRiskLevel]) -> str:
  if risk_level == PackageRiskLevel.DESTRUCTIVE:
    return 'danger'
  if risk_level == PackageRiskLevel.ADVANCED:
    return 'warning'
  return 'info'


def _evidence_tone(session_report: SessionEvidenceReport) -> str:
  if session_report.pit.state in ('failed', 'malformed'):
    return 'danger'
  if session_report.pit.device_alignment == 'mismatched':
    return 'danger'
  if session_report.pit.package_alignment == 'mismatched':
    return 'danger'
  if session_report.pit.device_alignment == 'not_provided':
    return 'warning'
  if session_report.pit.package_alignment in ('missing_reviewed', 'missing_observed'):
    return 'warning'
  if session_report.pit.state == 'partial':
    return 'warning'
  if session_report.outcome.outcome == 'failed':
    return 'danger'
  if session_report.outcome.outcome == 'resume_needed':
    return 'warning'
  if session_report.preflight.gate == 'blocked':
    return 'warning'
  if session_report.flash_plan.suspicious_warning_count:
    return 'warning'
  if session_report.outcome.export_ready:
    return 'success'
  return 'neutral'


def _transport_tone(state: str) -> str:
  if state == 'failed':
    return 'danger'
  if state == 'resume_needed':
    return 'warning'
  if state == 'completed':
    return 'success'
  if state in ('executing', 'detected'):
    return 'info'
  return 'neutral'


def _safe_path_governance_lines(
  session_report: SessionEvidenceReport,
) -> Tuple[str, ...]:
  transport = session_report.transport
  if (
    transport.capability != 'flash_package'
    or transport.command_display == 'not_invoked'
  ):
    return ()
  if transport.adapter_name == 'integrated-runtime':
    return (
      'Safe-path governance: platform-supervised bounded reviewed flash session',
      'Supported-path runtime: Calamum integrated runtime owns the operator-visible lane while delegated lower-transport details remain transcript-preserved.',
    )
  return (
    'Safe-path governance: platform-supervised bounded reviewed flash session',
    'Delegated boundary: Heimdall remains the lower transport lane while the platform owns gating, supervision, and evidence.',
  )


def _package_detail_lines(
  package_assessment: PackageManifestAssessment,
  reviewed_flash_plan: ReviewedFlashPlan,
  pit_inspection: Optional[PitInspection],
) -> Tuple[str, ...]:
  details = [
    'Package id: {package_id}'.format(
      package_id=package_assessment.display_package_id,
    ),
    'Source build: {source_build}'.format(
      source_build=package_assessment.source_build,
    ),
    'Compatibility summary: {summary}'.format(
      summary=package_assessment.compatibility_summary,
    ),
    'Supported product codes: {codes}'.format(
      codes=', '.join(package_assessment.supported_product_codes) or 'none declared',
    ),
    'Supported devices: {devices}'.format(
      devices=', '.join(package_assessment.supported_device_names) or 'none declared',
    ),
    'PIT fingerprint: {pit}'.format(
      pit=package_assessment.pit_fingerprint,
    ),
    'Suspiciousness summary: {summary}'.format(
      summary=package_assessment.suspiciousness_summary,
    ),
    'Flash plan id: {plan_id}'.format(
      plan_id=reviewed_flash_plan.plan_id,
    ),
    'Flash plan posture: {posture}'.format(
      posture=(
        'ready for transport review'
        if reviewed_flash_plan.ready_for_transport
        else 'blocked pending trust review'
      )
    ),
    'Transport backend: {backend} ({capabilities})'.format(
      backend=reviewed_flash_plan.transport_backend,
      capabilities=', '.join(reviewed_flash_plan.required_capabilities),
    ),
    'Reboot policy: {policy}'.format(
      policy=reviewed_flash_plan.reboot_policy,
    ),
  ]

  if package_assessment.detected_product_code is not None:
    if package_assessment.device_registry_known:
      details.append(
        'Detected device: {name} ({product_code})'.format(
          name=package_assessment.resolved_device_name or 'Samsung device',
          product_code=(
            package_assessment.resolved_product_code
            or package_assessment.detected_product_code
          ),
        )
      )
      details.append(
        'Registry resolution: {match}'.format(
          match=package_assessment.device_registry_match_kind.value,
        )
      )
    else:
      details.append(
        'Detected device: {product_code}'.format(
          product_code=package_assessment.detected_product_code,
        )
      )
      details.append('Registry resolution: unknown')
  if package_assessment.device_mode_entry_instructions:
    details.append(
      'Mode entry: {instruction}'.format(
        instruction=package_assessment.device_mode_entry_instructions[0],
      )
    )
  for quirk in package_assessment.device_known_quirks[:1]:
    details.append('Device quirk: {quirk}'.format(quirk=quirk))

  if pit_inspection is not None:
    details.append(
      'Observed PIT posture: {state}'.format(
        state=pit_inspection.state.value.replace('_', ' '),
      )
    )
    details.append(
      'Observed PIT fingerprint: {fingerprint}'.format(
        fingerprint=pit_inspection.observed_pit_fingerprint or 'unknown',
      )
    )
    details.append(
      'PIT/package alignment: {alignment}'.format(
        alignment=pit_inspection.package_alignment.value.replace('_', ' '),
      )
    )
    details.append(
      'PIT/device alignment: {alignment}'.format(
        alignment=pit_inspection.device_alignment.value.replace('_', ' '),
      )
    )
    if pit_inspection.partition_names:
      details.append(
        'Observed partitions: {partitions}'.format(
          partitions=', '.join(pit_inspection.partition_names),
        )
      )
    if pit_inspection.marketing_name is not None:
      details.append(
        'Observed PIT device: {name} ({product})'.format(
          name=pit_inspection.marketing_name,
          product=(
            pit_inspection.canonical_product_code
            or pit_inspection.observed_product_code
            or 'unknown'
          ),
        )
      )
    elif pit_inspection.observed_product_code is not None:
      details.append(
        'Observed PIT product code: {product}'.format(
          product=pit_inspection.observed_product_code,
        )
      )
    if pit_inspection.download_path:
      details.append(
        'PIT artifact path: {path}'.format(path=pit_inspection.download_path)
      )
    for guidance in pit_inspection.operator_guidance[:2]:
      details.append('PIT guidance: {guidance}'.format(guidance=guidance))

  if package_assessment.partitions:
    for partition in package_assessment.partitions[:3]:
      details.append(
        'Plan preview: {partition} <- {file_name}{required}'.format(
          partition=partition.partition_name,
          file_name=partition.file_name,
          required=' (required)' if partition.required else '',
        )
      )
  else:
    details.append('Plan preview: manifest does not yet provide usable partition rows.')

  if package_assessment.checksums:
    if package_assessment.checksum_verification_complete:
      details.append(
        'Checksum digests verified: {verified}/{total}'.format(
          verified=package_assessment.verified_checksum_count,
          total=len(package_assessment.checksums),
        )
      )
      for checksum in package_assessment.checksums[:2]:
        details.append(
          'Digest preview: {checksum_id} -> {digest}'.format(
            checksum_id=checksum.checksum_id,
            digest=checksum.display_value[:16] + '...',
          )
        )
      if package_assessment.source_kind != 'fixture':
        details.append(
          'Archive intake: normalized {count} checksum surfaces from {source}.'.format(
            count=len(package_assessment.checksums),
            source=package_assessment.fixture_name,
          )
        )
    else:
      details.append(
        'Checksum placeholders: {count}'.format(
          count=', '.join(checksum.checksum_id for checksum in package_assessment.checksums)
        )
      )
  else:
    details.append('Checksum placeholders: missing or incomplete.')

  for finding in package_assessment.suspicious_findings[:3]:
    details.append(
      'Suspicious trait: {title} ({evidence_source}: {evidence_value})'.format(
        title=finding.title,
        evidence_source=finding.evidence_source,
        evidence_value=finding.evidence_value,
      )
    )

  if package_assessment.analyzed_snapshot_id is not None:
    details.append(
      'Analyzed snapshot: {snapshot_id}'.format(
        snapshot_id=package_assessment.analyzed_snapshot_id,
      )
    )
    if package_assessment.analyzed_snapshot_verified:
      details.append('Snapshot verification: verified before execution review.')
    elif package_assessment.analyzed_snapshot_drift_detected:
      details.append('Snapshot verification: drift detected before execution.')
    else:
      details.append('Snapshot verification: pending re-verification.')
  elif package_assessment.source_kind == 'archive':
    details.append('Analyzed snapshot: not yet sealed for this archive review path.')

  for requirement in reviewed_flash_plan.advanced_requirements[:2]:
    details.append('Advanced requirement: {requirement}'.format(
      requirement=requirement,
    ))

  for blocker in reviewed_flash_plan.blocking_reasons[:2]:
    details.append('Flash plan blocker: {blocker}'.format(blocker=blocker))

  for guidance in reviewed_flash_plan.recovery_guidance[:2]:
    details.append('Recovery plan: {guidance}'.format(guidance=guidance))

  for issue in package_assessment.snapshot_issues[:3]:
    details.append('Snapshot issue: {issue}'.format(issue=issue))

  for instruction in package_assessment.post_flash_instructions[:2]:
    details.append('Post-flash: {instruction}'.format(instruction=instruction))

  for issue in package_assessment.contract_issues[:3]:
    details.append('Contract issue: {issue}'.format(issue=issue))

  return tuple(details)


def _preflight_detail_lines(report: PreflightReport) -> Tuple[str, ...]:
  details = []
  for signal in _top_preflight_signals(report):
    details.append(
      '{severity} — {summary}'.format(
        severity=signal.severity.value.upper(),
        summary=signal.summary,
      )
    )
  details.append(report.recommended_action)
  return tuple(details)


def _top_preflight_signals(
  report: PreflightReport,
) -> Tuple[PreflightSignal, ...]:
  ordered = []
  ordered.extend(
    signal for signal in report.signals if signal.severity == PreflightSeverity.BLOCK
  )
  ordered.extend(
    signal for signal in report.signals if signal.severity == PreflightSeverity.WARN
  )
  if not ordered:
    ordered.extend(
      signal for signal in report.signals if signal.severity == PreflightSeverity.PASS
    )
  else:
    ordered.extend(
      signal
      for signal in report.signals
      if signal.severity == PreflightSeverity.PASS
    )
  return tuple(ordered[:4])
"""GUI-safe view models that bind the FS-03 shell to platform state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.domain.device_registry import DeviceRegistryMatchKind
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.domain.flash_plan import ReviewedFlashPlan
from calamum_vulcan.domain.flash_plan import build_reviewed_flash_plan
from calamum_vulcan.domain.package import PackageCompatibilityExpectation
from calamum_vulcan.domain.package import PackageManifestAssessment
from calamum_vulcan.domain.package import PackageRiskLevel
from calamum_vulcan.domain.package import preflight_overrides_from_package_assessment
from calamum_vulcan.domain.preflight import PreflightGate
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import PreflightReport
from calamum_vulcan.domain.preflight import PreflightSeverity
from calamum_vulcan.domain.preflight import PreflightSignal
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.reporting import SessionEvidenceReport
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import SessionPhase


PANEL_TITLES = (
  'Device Identity',
  'Preflight Board',
  'Package Summary',
  'Transport State',
  'Session Evidence',
)

UNPOPULATED_VALUE = '--'

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


@dataclass(frozen=True)
class PanelViewModel:
  """Presentation contract for one dashboard card."""

  title: str
  eyebrow: str
  summary: str
  detail_lines: Tuple[str, ...] = ()
  metrics: Tuple[MetricViewModel, ...] = ()
  tone: str = 'neutral'


@dataclass(frozen=True)
class ControlActionViewModel:
  """A shell control-deck action with availability and emphasis."""

  label: str
  hint: str
  enabled: bool
  emphasis: str = 'normal'


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
  session: PlatformSession
  package_assessment: Optional[PackageManifestAssessment]
  transport_trace: Optional[HeimdallNormalizedTrace]
  live_device: Optional[LiveCompanionDeviceViewModel] = None
  boot_unhydrated: bool = False
  device_surface_cleared: bool = False


def build_shell_view_model(
  session: PlatformSession,
  scenario_name: str = 'Live session',
  preflight_report: Optional[PreflightReport] = None,
  package_assessment: Optional[PackageManifestAssessment] = None,
  transport_trace: Optional[HeimdallNormalizedTrace] = None,
  session_report: Optional[SessionEvidenceReport] = None,
  live_device: Optional[LiveCompanionDeviceViewModel] = None,
  boot_unhydrated: bool = False,
  device_surface_cleared: bool = False,
) -> ShellViewModel:
  """Build the FS-03 shell model directly from the immutable session."""

  phase_label = PHASE_LABELS[session.phase]
  phase_tone = PHASE_TONES[session.phase]
  report = preflight_report
  if report is None:
    report = _build_preflight_report(session, package_assessment)
  evidence_report = session_report
  if evidence_report is None:
    evidence_report = build_session_evidence_report(
      session,
      scenario_name=scenario_name,
      preflight_report=report,
      package_assessment=package_assessment,
      transport_trace=transport_trace,
    )
  return ShellViewModel(
    title='Calamum Vulcan',
    subtitle='Samsung operations console — reviewed-session GUI shell',
    scenario_name=scenario_name,
    phase_label=phase_label,
    phase_tone=phase_tone,
    gate_label='Standby' if boot_unhydrated else GATE_LABELS[report.gate],
    gate_tone='neutral' if boot_unhydrated else GATE_TONES[report.gate],
    status_pills=_build_status_pills(
      session,
      report,
      package_assessment,
      live_device,
      boot_unhydrated,
      device_surface_cleared,
    ),
    panels=_build_panels(
      session,
      report,
      package_assessment,
      evidence_report,
      live_device,
      boot_unhydrated,
      device_surface_cleared,
    ),
    control_actions=_build_control_actions(session, report, evidence_report),
    log_lines=evidence_report.log_lines,
    session=session,
    package_assessment=package_assessment,
    transport_trace=transport_trace,
    live_device=live_device,
    boot_unhydrated=boot_unhydrated,
    device_surface_cleared=device_surface_cleared,
  )


def describe_shell(model: ShellViewModel) -> str:
  """Return a concise shell summary for evidence and CLI inspection."""

  panel_titles = ', '.join(panel.title for panel in model.panels)
  enabled_actions = ', '.join(
    action.label for action in model.control_actions if action.enabled
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


def _build_status_pills(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  live_device: Optional[LiveCompanionDeviceViewModel],
  boot_unhydrated: bool,
  device_surface_cleared: bool,
) -> Tuple[StatusPillViewModel, ...]:
  if boot_unhydrated:
    risk_value = UNPOPULATED_VALUE
    risk_tone = 'neutral'
    device_value = UNPOPULATED_VALUE
    device_tone = 'neutral'
    package_value = UNPOPULATED_VALUE
    package_tone = 'neutral'
  else:
    risk_value = _package_risk_value(session, package_assessment)
    risk_tone = 'neutral'
    if risk_value == 'destructive':
      risk_tone = 'danger'
    elif risk_value == 'standard':
      risk_tone = 'info'
    elif risk_value == 'advanced':
      risk_tone = 'warning'

    if device_surface_cleared and live_device is None:
      device_value = UNPOPULATED_VALUE
      device_tone = 'neutral'
    else:
      device_value = _device_pill_value(session, live_device)
      device_tone = 'info' if session.guards.has_device or live_device is not None else 'neutral'
      if live_device is not None and live_device.state == 'device':
        device_tone = 'success'
      elif live_device is not None and live_device.state != 'device':
        device_tone = 'warning'

    package_value = _package_label_value(session, package_assessment)
    package_tone = 'info' if session.guards.package_loaded else 'neutral'

  return (
    StatusPillViewModel(
      label='Phase',
      value=PHASE_LABELS[session.phase],
      tone=PHASE_TONES[session.phase],
    ),
    StatusPillViewModel(
      label='Gate',
      value=GATE_LABELS[report.gate],
      tone=GATE_TONES[report.gate],
    ),
    StatusPillViewModel(
      label='Device',
      value=device_value,
      tone=device_tone,
    ),
    StatusPillViewModel(
      label='Package',
      value=package_value,
      tone=package_tone,
    ),
    StatusPillViewModel(
      label='Risk',
      value=risk_value.upper(),
      tone=risk_tone,
    ),
  )


def _build_panels(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  session_report: SessionEvidenceReport,
  live_device: Optional[LiveCompanionDeviceViewModel],
  boot_unhydrated: bool,
  device_surface_cleared: bool,
) -> Tuple[PanelViewModel, ...]:
  return (
    _build_device_panel(
      session,
      live_device,
      boot_unhydrated,
      device_surface_cleared,
    ),
    _build_preflight_panel(session, report, boot_unhydrated),
    _build_package_panel(session, package_assessment, boot_unhydrated),
    _build_transport_panel(session, session_report, boot_unhydrated),
    _build_evidence_panel(session_report, boot_unhydrated),
  )


def _build_device_panel(
  session: PlatformSession,
  live_device: Optional[LiveCompanionDeviceViewModel],
  boot_unhydrated: bool,
  device_surface_cleared: bool,
) -> PanelViewModel:
  live_product_code = _live_product_code(live_device)
  device_resolution = resolve_device_profile(live_product_code or session.product_code)
  if boot_unhydrated and live_device is None:
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
  if device_surface_cleared and live_device is None:
    return PanelViewModel(
      title='Device Identity',
      eyebrow='DEVICE',
      summary='No live device is currently detected.',
      detail_lines=(
        'Latest detect: no device found.',
        'Next action: reconnect and run Detect device again.',
      ),
      metrics=(
        MetricViewModel('Presence', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Product code', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Registry', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Mode', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='neutral',
    )
  if live_device is not None:
    backend_label = live_device.backend.upper()
    summary = 'Live companion detected {device} via {backend} while the reviewed session remains {phase}.'.format(
      device=_live_device_summary_identity(live_device, device_resolution),
      backend=backend_label,
      phase=PHASE_LABELS[session.phase],
    )
    details = [
      'Live serial: {serial}'.format(serial=live_device.serial),
      'Live companion backend: {backend}'.format(backend=backend_label),
      'Live state: {state}'.format(state=live_device.state),
      'Live transport: {transport}'.format(transport=live_device.transport),
      'Reviewed session phase: {phase}'.format(phase=PHASE_LABELS[session.phase]),
    ]
    if live_product_code is not None:
      details.append(
        'Live product code: {product_code}'.format(product_code=live_product_code)
      )
    if live_device.model_name is not None and live_device.model_name != live_product_code:
      details.append('Live model: {model}'.format(model=live_device.model_name))
    if live_device.device_name is not None:
      details.append(
        'Live device codename: {device}'.format(device=live_device.device_name)
      )
    if session.mode is not None:
      details.append(
        'Reviewed session mode: {mode}'.format(mode=session.mode)
      )

    if device_resolution.known:
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
      registry_value = device_resolution.match_kind.value
      registry_tone = 'success'
      if device_resolution.match_kind == DeviceRegistryMatchKind.ALIAS:
        registry_tone = 'info'
    else:
      details.extend(
        (
          'Registry match: unknown',
          'Add a repo-owned device profile before trusting compatibility resolution.',
        )
      )
      registry_value = 'unknown'
      registry_tone = 'warning'

    tone = 'success' if live_device.state == 'device' else 'warning'
    metrics = (
      MetricViewModel('Presence', 'live', tone),
      MetricViewModel('Product code', live_product_code or 'unknown', 'info'),
      MetricViewModel('Registry', registry_value, registry_tone),
      MetricViewModel(
        'Mode',
        '{backend}/{state}'.format(
          backend=live_device.backend,
          state=live_device.state,
        ),
        tone,
      ),
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
  live_device: Optional[LiveCompanionDeviceViewModel],
) -> str:
  if live_device is None:
    return session.product_code or 'awaiting device'
  product_code = _live_product_code(live_device)
  if product_code is not None:
    return '{product_code} via {backend}'.format(
      product_code=product_code,
      backend=live_device.backend.upper(),
    )
  return '{serial} via {backend}'.format(
    serial=live_device.serial,
    backend=live_device.backend.upper(),
  )


def _live_product_code(
  live_device: Optional[LiveCompanionDeviceViewModel],
) -> Optional[str]:
  if live_device is None:
    return None
  if live_device.product_code is not None:
    return live_device.product_code
  if live_device.model_name is not None:
    return live_device.model_name
  return None


def _live_device_summary_identity(
  live_device: LiveCompanionDeviceViewModel,
  device_resolution,
) -> str:
  if device_resolution.known:
    return '{name} ({product_code})'.format(
      name=device_resolution.marketing_name or 'Samsung device',
      product_code=(
        device_resolution.canonical_product_code
        or device_resolution.detected_product_code
        or live_device.serial
      ),
    )
  live_product_code = _live_product_code(live_device)
  if live_product_code is not None:
    return '{product_code} [{serial}]'.format(
      product_code=live_product_code,
      serial=live_device.serial,
    )
  return live_device.serial


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
      GATE_LABELS[report.gate],
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
  reviewed_flash_plan = build_reviewed_flash_plan(package_assessment)
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
    detail_lines=_package_detail_lines(package_assessment, reviewed_flash_plan),
    metrics=metrics,
    tone=tone,
  )


def _build_transport_panel(
  session: PlatformSession,
  session_report: SessionEvidenceReport,
  boot_unhydrated: bool,
) -> PanelViewModel:
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
        MetricViewModel('Phase', PHASE_LABELS[session.phase], PHASE_TONES[session.phase]),
        MetricViewModel('Transport', 'standby', 'neutral'),
        MetricViewModel('Exit code', UNPOPULATED_VALUE, 'neutral'),
        MetricViewModel('Mode', UNPOPULATED_VALUE, 'neutral'),
      ),
      tone='neutral',
    )
  transport = session_report.transport
  tone = _transport_tone(transport.state)
  details = [
    'Adapter: {adapter}'.format(adapter=transport.adapter_name),
    'Capability: {capability}'.format(capability=transport.capability),
    'Command: {command}'.format(command=transport.command_display),
    'Normalized events: {count}'.format(count=transport.normalized_event_count),
  ]
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
    MetricViewModel('Phase', PHASE_LABELS[session.phase], PHASE_TONES[session.phase]),
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
) -> Tuple[ControlActionViewModel, ...]:
  execute_enabled = (
    session.phase == SessionPhase.READY_TO_EXECUTE
    and report.ready_for_execution
  )
  execute_emphasis = 'primary'
  if session.package_risk == 'destructive':
    execute_emphasis = 'danger'

  return (
    ControlActionViewModel(
      label='Detect device',
      hint='Probe Samsung download-mode presence and identity.',
      enabled=True,
      emphasis='normal',
    ),
    ControlActionViewModel(
      label='Load package',
      hint='Stage firmware metadata for compatibility review.',
      enabled=True,
      emphasis='normal',
    ),
    ControlActionViewModel(
      label='Review preflight',
      hint='Open the trust gate before any flash activity is possible.',
      enabled=session.guards.has_device and session.guards.package_loaded,
      emphasis='primary' if session.guards.has_device else 'normal',
    ),
    ControlActionViewModel(
      label='Execute flash plan',
      hint='Dangerously gated action kept visually separate on purpose.',
      enabled=execute_enabled,
      emphasis=execute_emphasis,
    ),
    ControlActionViewModel(
      label='Resume workflow',
      hint='Available only when a no-reboot or manual step is pending.',
      enabled=session.phase == SessionPhase.RESUME_NEEDED,
      emphasis='warning',
    ),
    ControlActionViewModel(
      label='Export evidence',
      hint='Render the FS-06 evidence bundle for review or archival.',
      enabled=session_report.outcome.export_ready,
      emphasis='primary' if session_report.outcome.export_ready else 'normal',
    ),
  )


def _build_preflight_report(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
) -> PreflightReport:
  if package_assessment is None:
    return evaluate_preflight(PreflightInput.from_session(session))
  overrides = preflight_overrides_from_package_assessment(package_assessment)
  return evaluate_preflight(PreflightInput.from_session(session, **overrides))


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


def _package_detail_lines(
  package_assessment: PackageManifestAssessment,
  reviewed_flash_plan: ReviewedFlashPlan,
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
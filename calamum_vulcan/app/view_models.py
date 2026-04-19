"""GUI-safe view models that bind the FS-03 shell to platform state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
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


def build_shell_view_model(
  session: PlatformSession,
  scenario_name: str = 'Live session',
  preflight_report: Optional[PreflightReport] = None,
  package_assessment: Optional[PackageManifestAssessment] = None,
  transport_trace: Optional[HeimdallNormalizedTrace] = None,
  session_report: Optional[SessionEvidenceReport] = None,
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
    subtitle='Samsung operations console — Sprint 0.1.0 GUI shell',
    scenario_name=scenario_name,
    phase_label=phase_label,
    phase_tone=phase_tone,
    gate_label=GATE_LABELS[report.gate],
    gate_tone=GATE_TONES[report.gate],
    status_pills=_build_status_pills(session, report, package_assessment),
    panels=_build_panels(session, report, package_assessment, evidence_report),
    control_actions=_build_control_actions(session, report, evidence_report),
    log_lines=evidence_report.log_lines,
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
) -> Tuple[StatusPillViewModel, ...]:
  risk_value = _package_risk_value(session, package_assessment)
  risk_tone = 'neutral'
  if risk_value == 'destructive':
    risk_tone = 'danger'
  elif risk_value == 'standard':
    risk_tone = 'info'
  elif risk_value == 'advanced':
    risk_tone = 'warning'

  device_value = session.product_code or 'awaiting device'
  device_tone = 'info' if session.guards.has_device else 'neutral'

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
) -> Tuple[PanelViewModel, ...]:
  return (
    _build_device_panel(session),
    _build_preflight_panel(session, report),
    _build_package_panel(session, package_assessment),
    _build_transport_panel(session, session_report),
    _build_evidence_panel(session_report),
  )


def _build_device_panel(session: PlatformSession) -> PanelViewModel:
  if session.guards.has_device:
    summary = '{product} ready for shell review'.format(
      product=session.product_code or 'Samsung device'
    )
    details = (
      'Mode: {mode}'.format(mode=session.mode or 'unknown'),
      'Device id: {device_id}'.format(
        device_id=session.device_id or 'pending registry lookup'
      ),
      'Marketing-name resolution stays deferred to the device registry.',
    )
    tone = 'info'
  else:
    summary = 'No Samsung download-mode device detected yet.'
    details = (
      'The GUI shell remains useful before hardware is attached.',
      'Fixture-driven layouts prevent backend pressure from leaking upward.',
    )
    tone = 'neutral'

  metrics = (
    MetricViewModel('Presence', 'present' if session.guards.has_device else 'none', tone),
    MetricViewModel('Product code', session.product_code or 'unknown', 'info'),
    MetricViewModel('Mode', session.mode or 'idle', 'neutral'),
  )
  return PanelViewModel(
    title='Device Identity',
    eyebrow='DEVICE',
    summary=summary,
    detail_lines=details,
    metrics=metrics,
    tone=tone,
  )


def _build_preflight_panel(
  session: PlatformSession,
  report: PreflightReport,
) -> PanelViewModel:
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
) -> PanelViewModel:
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
        'Partition preview and checksum surfaces arrive in FS-05.',
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
  tone = _package_panel_tone(package_assessment)
  if package_assessment.contract_issues:
    summary = '{name} manifest needs correction before a trusted flash plan can exist.'.format(
      name=package_assessment.display_name,
    )
  elif (
    session.guards.has_device
    and not package_assessment.matches_detected_product_code
  ):
    summary = '{name} does not match the detected Samsung product code.'.format(
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
    detail_lines=_package_detail_lines(package_assessment),
    metrics=metrics,
    tone=tone,
  )


def _build_transport_panel(
  session: PlatformSession,
  session_report: SessionEvidenceReport,
) -> PanelViewModel:
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


def _build_evidence_panel(session_report: SessionEvidenceReport) -> PanelViewModel:
  tone = _evidence_tone(session_report)
  details = [
    'Report id: {report_id}'.format(
      report_id=session_report.report_id,
    ),
    'Captured at: {captured}'.format(
      captured=session_report.captured_at_utc,
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
) -> Tuple[str, ...]:
  details = [
    'Package id: {package_id}'.format(
      package_id=package_assessment.display_package_id,
    ),
    'Source build: {source_build}'.format(
      source_build=package_assessment.source_build,
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
  ]

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
    details.append(
      'Checksum placeholders: {count}'.format(
        count=', '.join(checksum.checksum_id for checksum in package_assessment.checksums)
      )
    )
  else:
    details.append('Checksum placeholders: missing or incomplete.')

  for instruction in package_assessment.post_flash_instructions[:2]:
    details.append('Post-flash: {instruction}'.format(instruction=instruction))

  for issue in package_assessment.contract_issues[:3]:
    details.append('Contract issue: {issue}'.format(issue=issue))

  return tuple(details)


def _preflight_detail_lines(report: PreflightReport) -> Tuple[str, ...]:
  details = []
  for signal in _top_preflight_signals(report):
    details.append(
      '{severity} — {title}: {summary}'.format(
        severity=signal.severity.value.upper(),
        title=signal.title,
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
"""Evidence builders and serializers for the Calamum Vulcan FS-06 lane."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
import platform
import sys
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.adapters.heimdall import HeimdallTraceState
from calamum_vulcan.domain.package import PackageManifestAssessment
from calamum_vulcan.domain.package import preflight_overrides_from_package_assessment
from calamum_vulcan.domain.preflight import PreflightInput
from calamum_vulcan.domain.preflight import PreflightReport
from calamum_vulcan.domain.preflight import PreflightSeverity
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import SessionPhase

from .model import DeviceEvidence
from .model import DecisionTraceEntry
from .model import HostEnvironmentEvidence
from .model import OutcomeEvidence
from .model import PackageEvidence
from .model import PreflightEvidence
from .model import REPORT_EXPORT_TARGETS
from .model import SessionEvidenceReport
from .model import TransportEvidence


def build_session_evidence_report(
  session: PlatformSession,
  scenario_name: str = 'Live session',
  preflight_report: Optional[PreflightReport] = None,
  package_assessment: Optional[PackageManifestAssessment] = None,
  transport_trace: Optional[HeimdallNormalizedTrace] = None,
  captured_at_utc: Optional[str] = None,
) -> SessionEvidenceReport:
  """Build one structured evidence bundle for the current shell session."""

  report = preflight_report
  if report is None:
    report = _build_preflight_report(session, package_assessment)

  captured = captured_at_utc or _utc_now()
  host = HostEnvironmentEvidence(
    runtime='python {major}.{minor}.{micro}'.format(
      major=sys.version_info[0],
      minor=sys.version_info[1],
      micro=sys.version_info[2],
    ),
    platform=platform.system().lower(),
    execution_posture='fixture_first_adapter_late',
  )
  device = DeviceEvidence(
    device_present=session.guards.has_device,
    device_id=session.device_id,
    product_code=session.product_code,
    mode=session.mode,
  )
  package = _build_package_evidence(session, package_assessment)
  preflight = PreflightEvidence(
    gate=report.gate.value,
    ready_for_execution=report.ready_for_execution,
    summary=report.summary,
    recommended_action=report.recommended_action,
    pass_count=report.pass_count,
    warning_count=report.warning_count,
    block_count=report.block_count,
  )
  transport = _build_transport_evidence(session, transport_trace)
  outcome = OutcomeEvidence(
    outcome=_outcome_label(session),
    export_ready=_export_ready(session),
    next_action=_next_action(session, report),
    failure_reason=session.failure_reason,
    recovery_guidance=_recovery_guidance(
      session,
      report,
      package_assessment,
      transport_trace,
    ),
  )
  decision_trace = _build_decision_trace(
    session,
    report,
    package_assessment,
    transport_trace,
  )
  summary = _summary_for_session(session, report, outcome)
  report_id = _report_id(captured, session, scenario_name)
  log_lines = _build_log_lines(
    session,
    report,
    package_assessment,
    transport_trace,
    captured,
    report_id,
    summary,
    outcome,
    decision_trace,
  )

  return SessionEvidenceReport(
    schema_version='0.1.0',
    report_id=report_id,
    captured_at_utc=captured,
    scenario_name=scenario_name,
    session_phase=session.phase.value,
    summary=summary,
    host=host,
    device=device,
    package=package,
    preflight=preflight,
    transport=transport,
    outcome=outcome,
    decision_trace=decision_trace,
    log_lines=log_lines,
  )


def serialize_session_evidence_json(report: SessionEvidenceReport) -> str:
  """Render one evidence bundle as formatted JSON."""

  return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def render_session_evidence_markdown(report: SessionEvidenceReport) -> str:
  """Render one evidence bundle as a readable Markdown summary."""

  lines = [
    '## Calamum Vulcan session evidence',
    '',
    '- report id: `{report_id}`'.format(report_id=report.report_id),
    '- captured at: `{captured}`'.format(captured=report.captured_at_utc),
    '- scenario: `{scenario}`'.format(scenario=report.scenario_name),
    '- phase: `{phase}`'.format(phase=report.session_phase),
    '- gate: `{gate}`'.format(gate=report.preflight.gate),
    '- outcome: `{outcome}`'.format(outcome=report.outcome.outcome),
    '',
    '### Summary',
    '',
    report.summary,
    '',
    '### Device',
    '',
    '- present: `{present}`'.format(
      present='yes' if report.device.device_present else 'no'
    ),
    '- product code: `{product}`'.format(
      product=report.device.product_code or 'unknown'
    ),
    '- mode: `{mode}`'.format(mode=report.device.mode or 'idle'),
    '',
    '### Package',
    '',
    '- package id: `{package_id}`'.format(package_id=report.package.package_id),
    '- display name: `{name}`'.format(name=report.package.display_name),
    '- compatibility: `{compatibility}`'.format(
      compatibility=report.package.compatibility_expectation
    ),
    '- contract complete: `{complete}`'.format(
      complete='yes' if report.package.contract_complete else 'no'
    ),
    '- plan surface: `{partitions}` partitions / `{checksums}` checksums'.format(
      partitions=report.package.partition_count,
      checksums=report.package.checksum_count,
    ),
    '',
    '### Preflight',
    '',
    '- passes: `{passes}`'.format(passes=report.preflight.pass_count),
    '- warnings: `{warnings}`'.format(warnings=report.preflight.warning_count),
    '- blocks: `{blocks}`'.format(blocks=report.preflight.block_count),
    '- recommended action: {action}'.format(
      action=report.preflight.recommended_action
    ),
    '',
    '### Transport',
    '',
    '- adapter: `{adapter}`'.format(adapter=report.transport.adapter_name),
    '- capability: `{capability}`'.format(capability=report.transport.capability),
    '- state: `{state}`'.format(state=report.transport.state),
    '- command: `{command}`'.format(command=report.transport.command_display),
    '- normalized events: `{count}`'.format(
      count=report.transport.normalized_event_count,
    ),
  ]
  if report.transport.progress_markers:
    lines.append('- progress: `{progress}`'.format(
      progress=', '.join(report.transport.progress_markers),
    ))
  for note in report.transport.notes:
    lines.append('- note: {note}'.format(note=note))
  if report.outcome.failure_reason:
    lines.append('- failure reason: `{reason}`'.format(
      reason=report.outcome.failure_reason,
    ))
  lines.extend(['', '### Recovery guidance', ''])
  for guidance in report.outcome.recovery_guidance:
    lines.append('- {guidance}'.format(guidance=guidance))
  lines.extend(['', '### Decision trace', ''])
  for entry in report.decision_trace:
    lines.append(
      '- **{label}** [{source}/{severity}] — {summary}'.format(
        label=entry.label,
        source=entry.source,
        severity=entry.severity,
        summary=entry.summary,
      )
    )
  return '\n'.join(lines)


def write_session_evidence_report(
  report: SessionEvidenceReport,
  output_path: Path,
  format_name: str = 'json',
) -> Path:
  """Write one evidence bundle to disk in the requested format."""

  content = serialize_session_evidence_json(report)
  if format_name == 'markdown':
    content = render_session_evidence_markdown(report)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(content, encoding='utf-8')
  return output_path


def _build_preflight_report(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
) -> PreflightReport:
  if package_assessment is None:
    return evaluate_preflight(PreflightInput.from_session(session))
  overrides = preflight_overrides_from_package_assessment(package_assessment)
  return evaluate_preflight(PreflightInput.from_session(session, **overrides))


def _build_package_evidence(
  session: PlatformSession,
  package_assessment: Optional[PackageManifestAssessment],
) -> PackageEvidence:
  if package_assessment is None:
    return PackageEvidence(
      fixture_name=None,
      package_id=session.package_id or 'awaiting-package',
      display_name=session.package_id or 'Awaiting package',
      version='unknown',
      source_build='unknown',
      risk_level=session.package_risk or 'unclassified',
      compatibility_expectation='unknown',
      contract_complete=False,
      issue_count=0,
      partition_count=0,
      checksum_count=0,
    )

  return PackageEvidence(
    fixture_name=package_assessment.fixture_name,
    package_id=package_assessment.display_package_id,
    display_name=package_assessment.display_name,
    version=package_assessment.version,
    source_build=package_assessment.source_build,
    risk_level=(
      package_assessment.risk_level.value
      if package_assessment.risk_level is not None
      else 'unclassified'
    ),
    compatibility_expectation=package_assessment.compatibility_expectation.value,
    contract_complete=package_assessment.contract_complete,
    issue_count=len(package_assessment.contract_issues),
    partition_count=len(package_assessment.partitions),
    checksum_count=len(package_assessment.checksums),
    contract_issues=package_assessment.contract_issues,
  )


def _build_transport_evidence(
  session: PlatformSession,
  transport_trace: Optional[HeimdallNormalizedTrace],
) -> TransportEvidence:
  if transport_trace is None:
    return TransportEvidence(
      adapter_name='heimdall',
      capability='reserved',
      command_display='not_invoked',
      state=_fallback_transport_state(session).value,
      summary='Transport remains behind the Heimdall adapter boundary until the shell invokes a normalized backend trace.',
      exit_code=None,
      normalized_event_count=0,
    )

  return TransportEvidence(
    adapter_name='heimdall',
    capability=transport_trace.command_plan.capability.value,
    command_display=transport_trace.command_plan.display_command,
    state=transport_trace.state.value,
    summary=transport_trace.summary,
    exit_code=transport_trace.exit_code,
    normalized_event_count=len(transport_trace.platform_events),
    progress_markers=transport_trace.progress_markers,
    notes=transport_trace.notes,
  )


def _outcome_label(session: PlatformSession) -> str:
  if session.phase == SessionPhase.COMPLETED:
    return 'completed'
  if session.phase == SessionPhase.FAILED:
    return 'failed'
  if session.phase == SessionPhase.RESUME_NEEDED:
    return 'resume_needed'
  if session.phase == SessionPhase.READY_TO_EXECUTE:
    return 'ready_to_execute'
  if session.phase == SessionPhase.VALIDATION_BLOCKED:
    return 'validation_blocked'
  return 'in_progress'


def _export_ready(session: PlatformSession) -> bool:
  return (
    session.last_event is not None
    or session.guards.has_device
    or session.guards.package_loaded
  )


def _next_action(
  session: PlatformSession,
  report: PreflightReport,
) -> str:
  if session.phase == SessionPhase.FAILED:
    return 'Review normalized failure evidence before attempting any retry.'
  if session.phase == SessionPhase.RESUME_NEEDED:
    return 'Complete the manual resume step before transport continues.'
  if report.gate == report.gate.BLOCKED:
    return report.recommended_action
  if report.gate == report.gate.WARN:
    return 'Resolve or acknowledge the warning findings before execution.'
  if session.phase == SessionPhase.READY_TO_EXECUTE:
    return 'Review the separated execute control and export the evidence bundle if needed.'
  return 'Continue the fixture-driven review path and preserve the evidence trail.'


def _summary_for_session(
  session: PlatformSession,
  report: PreflightReport,
  outcome: OutcomeEvidence,
) -> str:
  if session.phase == SessionPhase.COMPLETED:
    return 'Session completed cleanly and the evidence bundle is ready for export.'
  if session.phase == SessionPhase.FAILED:
    return 'Session failed, and the evidence bundle preserves recovery guidance before adapter work begins.'
  if session.phase == SessionPhase.RESUME_NEEDED:
    return 'Session paused for manual recovery and the evidence bundle preserves the resume path.'
  if report.gate == report.gate.BLOCKED:
    return 'Session is blocked before execution, and the evidence bundle captures the trust findings.'
  if report.gate == report.gate.WARN:
    return 'Session is warning-gated, and the evidence bundle records the required operator caution.'
  if outcome.export_ready:
    return 'Session evidence is live and exportable for the current operator review state.'
  return 'Session evidence contract is initialized and waiting for meaningful session activity.'


def _recovery_guidance(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  transport_trace: Optional[HeimdallNormalizedTrace],
) -> Tuple[str, ...]:
  guidance = []
  if session.phase == SessionPhase.FAILED:
    guidance.append('Stabilize the direct USB path before any retry attempt.')
    guidance.append('Re-run the package and preflight review before restarting transport.')
  elif session.phase == SessionPhase.RESUME_NEEDED:
    guidance.append('Complete the manual recovery or reboot step recorded in the session notes.')
    guidance.append('Return to the shell only after the device is back in the expected mode.')
  elif report.gate == report.gate.BLOCKED:
    guidance.append(report.recommended_action)
    guidance.append('Do not enable the flash path until every blocking trust finding is cleared.')
  elif report.gate == report.gate.WARN:
    guidance.append('Resolve or explicitly acknowledge warnings before any execution path opens.')
  else:
    guidance.append('Preserve this evidence bundle before deeper adapter integration begins.')

  if package_assessment is not None and package_assessment.contract_issues:
    guidance.append('Repair the package manifest contract before treating the flash plan as trusted.')

  if transport_trace is not None and transport_trace.state == HeimdallTraceState.RESUME_NEEDED:
    guidance.append('Preserve the no-reboot handoff note before handing control back to the operator.')

  return tuple(guidance)


def _build_decision_trace(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  transport_trace: Optional[HeimdallNormalizedTrace],
) -> Tuple[DecisionTraceEntry, ...]:
  trace = [
    DecisionTraceEntry(
      source='phase',
      label='Session phase',
      summary=session.phase.value,
      severity='info',
    ),
    DecisionTraceEntry(
      source='preflight',
      label='Trust gate',
      summary=report.summary,
      severity=report.gate.value,
    ),
  ]

  for signal in _top_preflight_signals(report):
    trace.append(
      DecisionTraceEntry(
        source='preflight',
        label=signal.title,
        summary=signal.summary,
        severity=signal.severity.value,
      )
    )

  if package_assessment is not None:
    trace.append(
      DecisionTraceEntry(
        source='package',
        label='Package compatibility',
        summary=package_assessment.compatibility_expectation.value,
        severity='danger'
        if not package_assessment.matches_detected_product_code
        else 'success',
      )
    )
    for issue in package_assessment.contract_issues[:2]:
      trace.append(
        DecisionTraceEntry(
          source='package',
          label='Manifest issue',
          summary=issue,
          severity='danger',
        )
      )

  if transport_trace is not None:
    trace.append(
      DecisionTraceEntry(
        source='transport',
        label='Heimdall adapter',
        summary=transport_trace.summary,
        severity=_transport_severity(transport_trace.state),
      )
    )

  if session.failure_reason:
    trace.append(
      DecisionTraceEntry(
        source='outcome',
        label='Failure reason',
        summary=session.failure_reason,
        severity='danger',
      )
    )

  return tuple(trace[:8])


def _build_log_lines(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  transport_trace: Optional[HeimdallNormalizedTrace],
  captured_at_utc: str,
  report_id: str,
  summary: str,
  outcome: OutcomeEvidence,
  decision_trace: Tuple[DecisionTraceEntry, ...],
) -> Tuple[str, ...]:
  lines = [
    '[REPORT] {report_id} captured={captured}'.format(
      report_id=report_id,
      captured=captured_at_utc,
    ),
    '[SESSION] Calamum Vulcan shell bound to platform-owned state.',
    '[PHASE] {phase}'.format(phase=session.phase.value),
    '[GATE] {gate}'.format(gate=report.gate.value),
    '[DEVICE] {device}'.format(device=session.product_code or 'Awaiting device'),
    '[PACKAGE] {package}'.format(package=session.package_id or 'Awaiting package'),
  ]

  for signal in _top_preflight_signals(report):
    lines.append(
      '[PREFLIGHT] {severity} {title}: {summary}'.format(
        severity=signal.severity.value.upper(),
        title=signal.title,
        summary=signal.summary,
      )
    )

  if session.last_event:
    lines.append('[EVENT] {event}'.format(event=session.last_event.value))
  if session.preflight_notes:
    for note in session.preflight_notes:
      lines.append('[NOTE] {note}'.format(note=note))
  if package_assessment is not None:
    lines.append(
      '[PACKAGE-CTX] {fixture} / compatibility={compatibility} / partitions={partitions} / checksums={checksums}'.format(
        fixture=package_assessment.fixture_name,
        compatibility=package_assessment.compatibility_expectation.value,
        partitions=len(package_assessment.partitions),
        checksums=len(package_assessment.checksums),
      )
    )
    for issue in package_assessment.contract_issues[:3]:
      lines.append('[PACKAGE-ISSUE] {issue}'.format(issue=issue))
  if transport_trace is not None:
    lines.append(
      '[TRANSPORT] {capability} state={state} exit={exit_code}'.format(
        capability=transport_trace.command_plan.capability.value,
        state=transport_trace.state.value,
        exit_code=transport_trace.exit_code,
      )
    )
    lines.append('[COMMAND] {command}'.format(
      command=transport_trace.command_plan.display_command,
    ))
    for marker in transport_trace.progress_markers[:3]:
      lines.append('[PROGRESS] {marker}'.format(marker=marker))
    for note in transport_trace.notes[:2]:
      lines.append('[TRANSPORT-NOTE] {note}'.format(note=note))
  if session.failure_reason:
    lines.append('[FAILURE] {reason}'.format(reason=session.failure_reason))
  if session.phase == SessionPhase.RESUME_NEEDED:
    lines.append('[ACTION] Resume path must complete before flashing can continue.')
  if session.phase == SessionPhase.READY_TO_EXECUTE:
    lines.append('[ACTION] Operator may now review the separated execute control.')

  lines.append('[EVIDENCE] {summary}'.format(summary=summary))
  lines.append(
    '[EXPORT] {targets}'.format(targets=', '.join(REPORT_EXPORT_TARGETS))
  )
  lines.append('[NEXT] {next_action}'.format(next_action=outcome.next_action))
  if outcome.recovery_guidance:
    lines.append(
      '[RECOVERY] {guidance}'.format(guidance=outcome.recovery_guidance[0])
    )
  for trace in decision_trace[:2]:
    lines.append(
      '[TRACE] {label}: {summary}'.format(
        label=trace.label,
        summary=trace.summary,
      )
    )
  lines.append('[SHELL] GUI lane remains fixture-first and adapter-late.')
  return tuple(lines)


def _top_preflight_signals(
  report: PreflightReport,
) -> Tuple[object, ...]:
  ordered = []
  ordered.extend(
    signal for signal in report.signals if signal.severity == PreflightSeverity.BLOCK
  )
  ordered.extend(
    signal for signal in report.signals if signal.severity == PreflightSeverity.WARN
  )
  ordered.extend(
    signal for signal in report.signals if signal.severity == PreflightSeverity.PASS
  )
  return tuple(ordered[:4])


def _fallback_transport_state(session: PlatformSession) -> HeimdallTraceState:
  if session.phase == SessionPhase.FAILED:
    return HeimdallTraceState.FAILED
  if session.phase == SessionPhase.RESUME_NEEDED:
    return HeimdallTraceState.RESUME_NEEDED
  if session.phase in (SessionPhase.EXECUTING, SessionPhase.COMPLETED):
    return HeimdallTraceState.COMPLETED
  return HeimdallTraceState.NOT_INVOKED


def _transport_severity(state: HeimdallTraceState) -> str:
  if state == HeimdallTraceState.FAILED:
    return 'danger'
  if state == HeimdallTraceState.RESUME_NEEDED:
    return 'warning'
  if state == HeimdallTraceState.COMPLETED:
    return 'success'
  return 'info'


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    '+00:00',
    'Z',
  )


def _report_id(
  captured_at_utc: str,
  session: PlatformSession,
  scenario_name: str,
) -> str:
  normalized = captured_at_utc.replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')
  scenario_slug = scenario_name.lower().replace(' ', '-').replace('/', '-')
  return 'cv-{stamp}-{phase}-{scenario}'.format(
    stamp=normalized,
    phase=session.phase.value,
    scenario=scenario_slug,
  )
"""Evidence builders and serializers for the Calamum Vulcan FS-06 lane."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
import platform
import sys
from typing import Iterable
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.adapters.heimdall import HeimdallTraceState
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.domain.flash_plan import ReviewedFlashPlan
from calamum_vulcan.domain.flash_plan import build_reviewed_flash_plan
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
from .model import FlashPlanEvidence
from .model import HostEnvironmentEvidence
from .model import OutcomeEvidence
from .model import PackageEvidence
from .model import PreflightEvidence
from .model import REPORT_EXPORT_TARGETS
from .model import REPORT_SCHEMA_VERSION
from .model import SessionEvidenceReport
from .model import TranscriptEvidence
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
  reviewed_flash_plan = None  # type: Optional[ReviewedFlashPlan]
  if package_assessment is not None:
    reviewed_flash_plan = build_reviewed_flash_plan(package_assessment)

  captured = captured_at_utc or _utc_now()
  report_id = _report_id(captured, session, scenario_name)
  device_resolution = resolve_device_profile(session.product_code)
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
    product_code=device_resolution.detected_product_code,
    canonical_product_code=device_resolution.canonical_product_code,
    marketing_name=device_resolution.marketing_name,
    registry_match_kind=device_resolution.match_kind.value,
    mode=session.mode,
    mode_entry_instructions=device_resolution.mode_entry_instructions,
    known_quirks=device_resolution.known_quirks,
  )
  package = _build_package_evidence(session, package_assessment)
  flash_plan = _build_flash_plan_evidence(package_assessment, reviewed_flash_plan)
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
  transcript = _build_transcript_evidence(transport_trace, report_id)
  outcome = OutcomeEvidence(
    outcome=_outcome_label(session),
    export_ready=_export_ready(session),
    next_action=_next_action(session, report, flash_plan),
    failure_reason=session.failure_reason,
    recovery_guidance=_recovery_guidance(
      session,
      report,
      package_assessment,
      transport_trace,
      reviewed_flash_plan,
    ),
  )
  decision_trace = _build_decision_trace(
    session,
    report,
    package_assessment,
    transport_trace,
    reviewed_flash_plan,
  )
  summary = _summary_for_session(session, report, outcome, flash_plan, transcript)
  log_lines = _build_log_lines(
    session,
    report,
    package_assessment,
    transport_trace,
    reviewed_flash_plan,
    transcript,
    captured,
    report_id,
    summary,
    outcome,
    decision_trace,
  )

  return SessionEvidenceReport(
    schema_version=REPORT_SCHEMA_VERSION,
    report_id=report_id,
    captured_at_utc=captured,
    scenario_name=scenario_name,
    session_phase=session.phase.value,
    summary=summary,
    host=host,
    device=device,
    package=package,
    flash_plan=flash_plan,
    preflight=preflight,
    transport=transport,
    transcript=transcript,
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
    '- canonical product code: `{product}`'.format(
      product=report.device.canonical_product_code or 'unknown'
    ),
    '- marketing name: `{name}`'.format(
      name=report.device.marketing_name or 'unknown'
    ),
    '- registry match: `{match}`'.format(
      match=report.device.registry_match_kind,
    ),
    '- mode: `{mode}`'.format(mode=report.device.mode or 'idle'),
    '',
    '### Package',
    '',
    '- package id: `{package_id}`'.format(package_id=report.package.package_id),
    '- source kind: `{source_kind}`'.format(source_kind=report.package.source_kind),
    '- display name: `{name}`'.format(name=report.package.display_name),
    '- compatibility: `{compatibility}`'.format(
      compatibility=report.package.compatibility_expectation
    ),
    '- compatibility summary: {summary}'.format(
      summary=report.package.compatibility_summary,
    ),
    '- contract complete: `{complete}`'.format(
      complete='yes' if report.package.contract_complete else 'no'
    ),
    '- plan surface: `{partitions}` partitions / `{checksums}` checksums'.format(
      partitions=report.package.partition_count,
      checksums=report.package.checksum_count,
    ),
    '- checksum verification: `{verified}` ({count}/{total})'.format(
      verified='yes' if report.package.checksum_verification_complete else 'no',
      count=report.package.verified_checksum_count,
      total=report.package.checksum_count,
    ),
    '- analyzed snapshot: `{snapshot_id}`'.format(
      snapshot_id=report.package.snapshot_id or 'not sealed'
    ),
    '- snapshot verification: `{verified}`'.format(
      verified='yes' if report.package.snapshot_verified else 'no'
    ),
    '- snapshot drift detected: `{drift}`'.format(
      drift='yes' if report.package.snapshot_drift_detected else 'no'
    ),
    '- suspicious warnings: `{count}`'.format(
      count=report.package.suspicious_warning_count,
    ),
    '- suspiciousness summary: {summary}'.format(
      summary=report.package.suspiciousness_summary,
    ),
    '',
    '### Flash plan',
    '',
    '- plan id: `{plan_id}`'.format(plan_id=report.flash_plan.plan_id),
    '- ready for transport review: `{ready}`'.format(
      ready='yes' if report.flash_plan.ready_for_transport else 'no'
    ),
    '- transport backend: `{backend}`'.format(
      backend=report.flash_plan.transport_backend,
    ),
    '- summary: {summary}'.format(summary=report.flash_plan.summary),
    '- reboot policy: `{policy}`'.format(
      policy=report.flash_plan.reboot_policy,
    ),
    '- repartition allowed: `{allowed}`'.format(
      allowed='yes' if report.flash_plan.repartition_allowed else 'no'
    ),
    '- partition targets: `{targets}`'.format(
      targets=', '.join(report.flash_plan.partition_targets) or 'none'
    ),
    '- required capabilities: `{capabilities}`'.format(
      capabilities=', '.join(report.flash_plan.required_capabilities) or 'none'
    ),
    '- operator warnings: `{count}`'.format(
      count=report.flash_plan.suspicious_warning_count,
    ),
    '- verified partitions: `{verified}` / `{total}`'.format(
      verified=report.flash_plan.verified_partition_count,
      total=report.flash_plan.partition_count,
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
    '',
    '### Transcript',
    '',
    '- policy: `{policy}`'.format(policy=report.transcript.policy),
    '- preserved: `{preserved}`'.format(
      preserved='yes' if report.transcript.preserved else 'no'
    ),
    '- transcript lines: `{count}`'.format(
      count=report.transcript.line_count,
    ),
    '- transcript reference: `{reference}`'.format(
      reference=report.transcript.reference_file_name or 'not_preserved'
    ),
  ]
  flash_plan_detail_lines = []
  for requirement in report.flash_plan.advanced_requirements:
    flash_plan_detail_lines.append(
      '- flash-plan requirement: {requirement}'.format(
        requirement=requirement,
      )
    )
  for warning in report.flash_plan.operator_warnings:
    flash_plan_detail_lines.append(
      '- flash-plan warning: {warning}'.format(warning=warning)
    )
  for blocker in report.flash_plan.blocking_reasons:
    flash_plan_detail_lines.append(
      '- flash-plan blocker: {blocker}'.format(blocker=blocker)
    )
  if flash_plan_detail_lines:
    flash_plan_detail_lines.append('')
    preflight_index = lines.index('### Preflight')
    lines[preflight_index:preflight_index] = flash_plan_detail_lines
  if report.transport.progress_markers:
    lines.append('- progress: `{progress}`'.format(
      progress=', '.join(report.transport.progress_markers),
    ))
  if report.device.mode_entry_instructions:
    lines.append('- mode entry: {instruction}'.format(
      instruction=report.device.mode_entry_instructions[0],
    ))
  for quirk in report.device.known_quirks[:1]:
    lines.append('- device quirk: {quirk}'.format(quirk=quirk))
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
  transport_trace: Optional[HeimdallNormalizedTrace] = None,
) -> Path:
  """Write one evidence bundle to disk in the requested format."""

  content = serialize_session_evidence_json(report)
  if format_name == 'markdown':
    content = render_session_evidence_markdown(report)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(content, encoding='utf-8')
  if transport_trace is not None and report.transcript.preserved:
    transcript_path = output_path.parent / (
      report.transcript.reference_file_name or (output_path.stem + '.transport.log')
    )
    transcript_path.write_text(
      render_transport_transcript_text(report, transport_trace),
      encoding='utf-8',
    )
  return output_path


def render_transport_transcript_text(
  report: SessionEvidenceReport,
  transport_trace: HeimdallNormalizedTrace,
) -> str:
  """Render one bounded transport transcript as a plain-text artifact."""

  lines = [
    'Calamum Vulcan transport transcript',
    'report_id={report_id}'.format(report_id=report.report_id),
    'scenario={scenario}'.format(scenario=report.scenario_name),
    'captured_at_utc={captured}'.format(captured=report.captured_at_utc),
    'adapter=heimdall',
    'capability={capability}'.format(
      capability=transport_trace.command_plan.capability.value,
    ),
    'command={command}'.format(
      command=transport_trace.command_plan.display_command,
    ),
    'state={state}'.format(state=transport_trace.state.value),
    'exit_code={exit_code}'.format(exit_code=transport_trace.exit_code),
    'policy={policy}'.format(policy=report.transcript.policy),
    'summary={summary}'.format(summary=transport_trace.summary),
    '',
    '[progress_markers]',
  ]
  if transport_trace.progress_markers:
    lines.extend(transport_trace.progress_markers)
  else:
    lines.append('(none)')
  lines.extend(['', '[notes]'])
  if transport_trace.notes:
    lines.extend(transport_trace.notes)
  else:
    lines.append('(none)')
  lines.extend(['', '[stdout]'])
  if transport_trace.stdout_lines:
    lines.extend(transport_trace.stdout_lines)
  else:
    lines.append('(none)')
  lines.extend(['', '[stderr]'])
  if transport_trace.stderr_lines:
    lines.extend(transport_trace.stderr_lines)
  else:
    lines.append('(none)')
  return '\n'.join(lines) + '\n'


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
      source_kind='pending',
      package_id=session.package_id or 'awaiting-package',
      display_name=session.package_id or 'Awaiting package',
      version='unknown',
      source_build='unknown',
      risk_level=session.package_risk or 'unclassified',
      compatibility_expectation='unknown',
      compatibility_summary='Compatibility unresolved.',
      contract_complete=False,
      issue_count=0,
      partition_count=0,
      checksum_count=0,
      checksum_verification_complete=False,
      verified_checksum_count=0,
      snapshot_id=None,
      snapshot_created_at_utc=None,
      snapshot_verified=False,
      snapshot_drift_detected=False,
      snapshot_issue_count=0,
      suspicious_warning_count=0,
      suspiciousness_summary='No suspicious Android traits detected.',
    )

  return PackageEvidence(
    fixture_name=package_assessment.fixture_name,
    source_kind=package_assessment.source_kind,
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
    compatibility_summary=package_assessment.compatibility_summary,
    contract_complete=package_assessment.contract_complete,
    issue_count=len(package_assessment.contract_issues),
    partition_count=len(package_assessment.partitions),
    checksum_count=len(package_assessment.checksums),
    checksum_verification_complete=package_assessment.checksum_verification_complete,
    verified_checksum_count=package_assessment.verified_checksum_count,
    snapshot_id=package_assessment.analyzed_snapshot_id,
    snapshot_created_at_utc=package_assessment.analyzed_snapshot_created_at_utc,
    snapshot_verified=package_assessment.analyzed_snapshot_verified,
    snapshot_drift_detected=package_assessment.analyzed_snapshot_drift_detected,
    snapshot_issue_count=len(package_assessment.snapshot_issues),
    suspicious_warning_count=package_assessment.suspicious_warning_count,
    suspiciousness_summary=package_assessment.suspiciousness_summary,
    suspicious_indicator_ids=tuple(
      finding.indicator_id for finding in package_assessment.suspicious_findings
    ),
    suspicious_titles=tuple(
      finding.title for finding in package_assessment.suspicious_findings
    ),
    contract_issues=package_assessment.contract_issues,
    snapshot_issues=package_assessment.snapshot_issues,
  )


def _build_flash_plan_evidence(
  package_assessment: Optional[PackageManifestAssessment],
  reviewed_flash_plan: Optional[ReviewedFlashPlan],
) -> FlashPlanEvidence:
  if reviewed_flash_plan is None or package_assessment is None:
    return FlashPlanEvidence(
      schema_version='0.2.0-fs2-06',
      plan_id='pending',
      summary='Reviewed flash plan will be derived once a package assessment exists.',
      source_kind='pending',
      package_id='awaiting-package',
      snapshot_id=None,
      ready_for_transport=False,
      transport_backend='heimdall',
      risk_level='unclassified',
      reboot_policy='unspecified',
      repartition_allowed=False,
      pit_fingerprint='unknown',
      partition_count=0,
      required_partition_count=0,
      optional_partition_count=0,
      verified_partition_count=0,
      blocking_reasons=('Load and assess a package before transport review.',),
      recovery_guidance=('Load a package to derive reviewed recovery guidance.',),
    )

  return FlashPlanEvidence(
    schema_version=reviewed_flash_plan.schema_version,
    plan_id=reviewed_flash_plan.plan_id,
    summary=reviewed_flash_plan.summary,
    source_kind=reviewed_flash_plan.source_kind,
    package_id=reviewed_flash_plan.package_id,
    snapshot_id=reviewed_flash_plan.snapshot_id,
    ready_for_transport=reviewed_flash_plan.ready_for_transport,
    transport_backend=reviewed_flash_plan.transport_backend,
    risk_level=reviewed_flash_plan.risk_level,
    reboot_policy=reviewed_flash_plan.reboot_policy,
    repartition_allowed=reviewed_flash_plan.repartition_allowed,
    pit_fingerprint=reviewed_flash_plan.pit_fingerprint,
    partition_count=len(reviewed_flash_plan.partitions),
    required_partition_count=reviewed_flash_plan.required_partition_count,
    optional_partition_count=reviewed_flash_plan.optional_partition_count,
    verified_partition_count=reviewed_flash_plan.verified_partition_count,
    partition_targets=reviewed_flash_plan.partition_targets,
    partition_files=tuple(
      partition.file_name for partition in reviewed_flash_plan.partitions
    ),
    required_capabilities=reviewed_flash_plan.required_capabilities,
    advanced_requirements=reviewed_flash_plan.advanced_requirements,
    suspicious_warning_count=reviewed_flash_plan.suspicious_warning_count,
    operator_warnings=reviewed_flash_plan.operator_warnings,
    requires_operator_acknowledgement=reviewed_flash_plan.requires_operator_acknowledgement,
    blocking_reasons=reviewed_flash_plan.blocking_reasons,
    recovery_guidance=reviewed_flash_plan.recovery_guidance,
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


def _build_transcript_evidence(
  transport_trace: Optional[HeimdallNormalizedTrace],
  report_id: str,
) -> TranscriptEvidence:
  if transport_trace is None:
    return TranscriptEvidence(
      policy='summary_only',
      preserved=False,
      summary='No external transport transcript was preserved because transport was not invoked.',
      line_count=0,
    )

  stdout_count = len(transport_trace.stdout_lines)
  stderr_count = len(transport_trace.stderr_lines)
  return TranscriptEvidence(
    policy='preserve_bounded_transport_transcript',
    preserved=True,
    summary='Bounded Heimdall transport output is preserved as an external transcript artifact when evidence is written to disk.',
    line_count=stdout_count + stderr_count,
    stdout_line_count=stdout_count,
    stderr_line_count=stderr_count,
    progress_marker_count=len(transport_trace.progress_markers),
    note_count=len(transport_trace.notes),
    reference_file_name=report_id + '.transport.log',
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
  flash_plan: FlashPlanEvidence,
) -> str:
  if session.phase == SessionPhase.FAILED:
    return 'Review normalized failure evidence before attempting any retry.'
  if session.phase == SessionPhase.RESUME_NEEDED:
    return 'Complete the manual resume step before transport continues.'
  if report.gate == report.gate.BLOCKED:
    return report.recommended_action
  if report.gate == report.gate.WARN:
    return 'Resolve or acknowledge the warning findings before execution.'
  if not flash_plan.ready_for_transport:
    return 'Resolve the reviewed flash-plan blockers before any transport command is generated.'
  if session.phase == SessionPhase.READY_TO_EXECUTE:
    if flash_plan.suspicious_warning_count:
      return 'Review the acknowledged suspicious-trait warnings, flash plan, and separated execute control before transport.'
    return 'Review the reviewed flash plan, recovery guidance, and separated execute control before transport.'
  return 'Continue the fixture-driven review path and preserve the evidence trail.'


def _summary_for_session(
  session: PlatformSession,
  report: PreflightReport,
  outcome: OutcomeEvidence,
  flash_plan: FlashPlanEvidence,
  transcript: TranscriptEvidence,
) -> str:
  if session.phase == SessionPhase.COMPLETED:
    if transcript.preserved:
      return 'Session completed cleanly and the evidence bundle plus bounded transport transcript are ready for export.'
    return 'Session completed cleanly and the evidence bundle is ready for export.'
  if session.phase == SessionPhase.FAILED:
    if transcript.preserved:
      return 'Session failed, and the evidence bundle plus bounded transport transcript preserve recovery guidance before any retry.'
    return 'Session failed, and the evidence bundle preserves recovery guidance before adapter work begins.'
  if session.phase == SessionPhase.RESUME_NEEDED:
    if transcript.preserved:
      return 'Session paused for manual recovery and the evidence bundle plus bounded transport transcript preserve the resume path.'
    return 'Session paused for manual recovery and the evidence bundle preserves the resume path.'
  if report.gate == report.gate.BLOCKED:
    return 'Session is blocked before execution, and the evidence bundle captures the trust findings.'
  if report.gate == report.gate.WARN:
    return 'Session is warning-gated, and the evidence bundle records the required operator caution.'
  if flash_plan.suspicious_warning_count:
    return 'Session evidence is live and exportable; acknowledged warning-tier suspicious Android traits remain visible beside the reviewed flash plan.'
  if flash_plan.ready_for_transport and outcome.export_ready:
    return 'Session evidence is live and exportable; the reviewed flash plan and recovery guidance are ready for operator review.'
  if outcome.export_ready:
    return 'Session evidence is live and exportable for the current operator review state.'
  return 'Session evidence contract is initialized and waiting for meaningful session activity.'


def _recovery_guidance(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  transport_trace: Optional[HeimdallNormalizedTrace],
  reviewed_flash_plan: Optional[ReviewedFlashPlan],
) -> Tuple[str, ...]:
  guidance = []
  device_resolution = resolve_device_profile(session.product_code)
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

  if session.guards.has_device and not device_resolution.known:
    guidance.append('Do not proceed until the detected product code is represented in the repo-owned device registry.')

  if package_assessment is not None and package_assessment.contract_issues:
    guidance.append('Repair the package manifest contract before treating the flash plan as trusted.')
  if package_assessment is not None and package_assessment.suspicious_warning_count:
    guidance.append('Preserve explicit acknowledgement for the warning-tier suspicious Android traits before execution.')
  if package_assessment is not None and package_assessment.analyzed_snapshot_drift_detected:
    guidance.append('Re-import and re-seal the analyzed snapshot before execution.')
  elif package_assessment is not None and package_assessment.snapshot_issues:
    guidance.append('Seal and re-verify the analyzed snapshot before treating the current review path as execution-ready.')

  if transport_trace is not None and transport_trace.state == HeimdallTraceState.RESUME_NEEDED:
    guidance.append('Preserve the no-reboot handoff note before handing control back to the operator.')

  if reviewed_flash_plan is not None:
    guidance.extend(reviewed_flash_plan.recovery_guidance)
    if not reviewed_flash_plan.ready_for_transport:
      guidance.append(
        'Do not generate or execute a transport command until the reviewed flash-plan blockers are cleared.'
      )

  return tuple(_dedupe_strings(guidance))


def _build_decision_trace(
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  transport_trace: Optional[HeimdallNormalizedTrace],
  reviewed_flash_plan: Optional[ReviewedFlashPlan],
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
        summary=package_assessment.compatibility_summary,
        severity='danger'
        if not package_assessment.matches_detected_product_code
        else 'success',
      )
    )
    if package_assessment.analyzed_snapshot_id is not None:
      snapshot_severity = 'success'
      snapshot_summary = 'Analyzed snapshot verified for execution integrity.'
      if package_assessment.analyzed_snapshot_drift_detected:
        snapshot_severity = 'danger'
        snapshot_summary = 'Analyzed snapshot drift detected before execution.'
      elif not package_assessment.analyzed_snapshot_verified:
        snapshot_severity = 'warning'
        snapshot_summary = 'Analyzed snapshot has not yet been re-verified.'
      trace.append(
        DecisionTraceEntry(
          source='snapshot',
          label='Analyzed snapshot',
          summary=snapshot_summary,
          severity=snapshot_severity,
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
    for finding in package_assessment.suspicious_findings[:2]:
      trace.append(
        DecisionTraceEntry(
          source='package',
          label=finding.title,
          summary=finding.summary,
          severity='warning',
        )
      )
    for issue in package_assessment.snapshot_issues[:2]:
      trace.append(
        DecisionTraceEntry(
          source='snapshot',
          label='Snapshot issue',
          summary=issue,
          severity='danger',
        )
      )

  if reviewed_flash_plan is not None:
    trace.append(
      DecisionTraceEntry(
        source='flash_plan',
        label='Reviewed flash plan',
        summary=reviewed_flash_plan.summary,
        severity='success' if reviewed_flash_plan.ready_for_transport else 'danger',
      )
    )
    for blocker in reviewed_flash_plan.blocking_reasons[:2]:
      trace.append(
        DecisionTraceEntry(
          source='flash_plan',
          label='Flash-plan blocker',
          summary=blocker,
          severity='danger',
        )
      )
    for warning in reviewed_flash_plan.operator_warnings[:1]:
      trace.append(
        DecisionTraceEntry(
          source='flash_plan',
          label='Flash-plan warning',
          summary=warning,
          severity='warning',
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
  reviewed_flash_plan: Optional[ReviewedFlashPlan],
  transcript: TranscriptEvidence,
  captured_at_utc: str,
  report_id: str,
  summary: str,
  outcome: OutcomeEvidence,
  decision_trace: Tuple[DecisionTraceEntry, ...],
) -> Tuple[str, ...]:
  device_resolution = resolve_device_profile(session.product_code)
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
  if session.guards.has_device:
    lines.append(
      '[DEVICE-REGISTRY] match={match} canonical={canonical} name={name}'.format(
        match=device_resolution.match_kind.value,
        canonical=device_resolution.canonical_product_code or 'unknown',
        name=device_resolution.marketing_name or 'unknown',
      )
    )

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
      '[PACKAGE-CTX] {fixture} / source={source_kind} / compatibility={compatibility} / partitions={partitions} / checksums={checksums} / verified={verified}/{total}'.format(
        fixture=package_assessment.fixture_name,
        source_kind=package_assessment.source_kind,
        compatibility=package_assessment.compatibility_summary,
        partitions=len(package_assessment.partitions),
        checksums=len(package_assessment.checksums),
        verified=package_assessment.verified_checksum_count,
        total=len(package_assessment.checksums),
      )
    )
    if package_assessment.analyzed_snapshot_id is not None:
      lines.append(
        '[SNAPSHOT] {snapshot_id} verified={verified} drift={drift}'.format(
          snapshot_id=package_assessment.analyzed_snapshot_id,
          verified='yes' if package_assessment.analyzed_snapshot_verified else 'no',
          drift='yes' if package_assessment.analyzed_snapshot_drift_detected else 'no',
        )
      )
    for issue in package_assessment.contract_issues[:3]:
      lines.append('[PACKAGE-ISSUE] {issue}'.format(issue=issue))
    for finding in package_assessment.suspicious_findings[:3]:
      lines.append(
        '[SUSPICIOUS] {indicator}: {summary} ({evidence})'.format(
          indicator=finding.indicator_id,
          summary=finding.summary,
          evidence=finding.evidence_value,
        )
      )
    for issue in package_assessment.snapshot_issues[:3]:
      lines.append('[SNAPSHOT-ISSUE] {issue}'.format(issue=issue))
  if reviewed_flash_plan is not None:
    lines.append(
      '[FLASH-PLAN] {plan_id} ready={ready} backend={backend} reboot={reboot} repartition={repartition}'.format(
        plan_id=reviewed_flash_plan.plan_id,
        ready='yes' if reviewed_flash_plan.ready_for_transport else 'no',
        backend=reviewed_flash_plan.transport_backend,
        reboot=reviewed_flash_plan.reboot_policy,
        repartition='yes' if reviewed_flash_plan.repartition_allowed else 'no',
      )
    )
    lines.append(
      '[FLASH-TARGETS] {targets}'.format(
        targets=', '.join(reviewed_flash_plan.partition_targets) or 'none',
      )
    )
    for requirement in reviewed_flash_plan.advanced_requirements[:2]:
      lines.append('[FLASH-ADV] {requirement}'.format(requirement=requirement))
    for warning in reviewed_flash_plan.operator_warnings[:2]:
      lines.append('[FLASH-WARN] {warning}'.format(warning=warning))
    for blocker in reviewed_flash_plan.blocking_reasons[:2]:
      lines.append('[FLASH-BLOCKER] {blocker}'.format(blocker=blocker))
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
  if transcript.preserved:
    lines.append(
      '[TRANSCRIPT] policy={policy} lines={count} ref={reference}'.format(
        policy=transcript.policy,
        count=transcript.line_count,
        reference=transcript.reference_file_name or 'not_preserved',
      )
    )
  else:
    lines.append('[TRANSCRIPT] summary-only; no external transport transcript preserved.')
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


def _dedupe_strings(values: Iterable[str]) -> Tuple[str, ...]:
  deduped = []
  for value in values:
    if value not in deduped:
      deduped.append(value)
  return tuple(deduped)
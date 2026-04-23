"""Evidence builders and serializers for the Calamum Vulcan FS-06 lane."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
import platform
import re
import sys
from typing import Iterable
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.heimdall import HeimdallNormalizedTrace
from calamum_vulcan.adapters.heimdall import HeimdallTraceState
from calamum_vulcan.domain.device_registry import resolve_device_profile
from calamum_vulcan.domain.flash_plan import ReviewedFlashPlan
from calamum_vulcan.domain.flash_plan import build_reviewed_flash_plan
from calamum_vulcan.domain.live_device import LiveDeviceInfoState
from calamum_vulcan.domain.live_device import LiveDetectionState
from calamum_vulcan.domain.package import PackageManifestAssessment
from calamum_vulcan.domain.pit import PitDeviceAlignment
from calamum_vulcan.domain.pit import PitInspection
from calamum_vulcan.domain.pit import PitInspectionState
from calamum_vulcan.domain.pit import PitPackageAlignment
from calamum_vulcan.domain.preflight import PreflightReport
from calamum_vulcan.domain.preflight import PreflightSeverity
from calamum_vulcan.domain.preflight import evaluate_preflight
from calamum_vulcan.domain.preflight import preflight_input_from_review_context
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import SessionPhase
from calamum_vulcan.domain.state import build_session_authority_snapshot
from calamum_vulcan.domain.state.model import InspectionWorkflowPosture

from .model import DeviceEvidence
from .model import DecisionTraceEntry
from .model import FlashPlanEvidence
from .model import HostEnvironmentEvidence
from .model import InspectionWorkflowEvidence
from .model import LiveDeviceEvidence
from .model import LivePathIdentityEvidence
from .model import OutcomeEvidence
from .model import PackageEvidence
from .model import PitEvidence
from .model import PreflightEvidence
from .model import REPORT_EXPORT_TARGETS
from .model import REPORT_SCHEMA_VERSION
from .model import SessionAuthorityEvidence
from .model import SessionEvidenceReport
from .model import TranscriptEvidence
from .model import TransportEvidence


SAFE_FILE_COMPONENT_PATTERN = re.compile(r'[^A-Za-z0-9._-]+')
SAFE_DOT_RUN_PATTERN = re.compile(r'\.{2,}')


def build_session_evidence_report(
  session: PlatformSession,
  scenario_name: str = 'Live session',
  preflight_report: Optional[PreflightReport] = None,
  package_assessment: Optional[PackageManifestAssessment] = None,
  pit_inspection: Optional[PitInspection] = None,
  transport_trace: Optional[HeimdallNormalizedTrace] = None,
  captured_at_utc: Optional[str] = None,
  pit_required_for_safe_path: bool = False,
) -> SessionEvidenceReport:
  """Build one structured evidence bundle for the current shell session."""

  report = preflight_report
  if report is None:
    report = _build_preflight_report(
      session,
      package_assessment,
      pit_inspection,
      pit_required_for_safe_path=pit_required_for_safe_path,
    )
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
  authority = _build_session_authority_evidence(
    session,
    report,
    package_assessment,
    pit_inspection,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  inspection = _build_inspection_evidence(session)
  live = _build_live_device_evidence(session)
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
    live=live,
  )
  pit = _build_pit_evidence(pit_inspection)
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
    next_action=_next_action(
      session,
      report,
      flash_plan,
      authority,
      pit_inspection,
      transport_trace,
    ),
    failure_reason=session.failure_reason,
    recovery_guidance=_recovery_guidance(
      authority,
      session,
      report,
      package_assessment,
      pit_inspection,
      transport_trace,
      reviewed_flash_plan,
    ),
  )
  decision_trace = _build_decision_trace(
    authority,
    session,
    report,
    package_assessment,
    pit_inspection,
    transport_trace,
    reviewed_flash_plan,
  )
  summary = _summary_for_session(session, report, outcome, flash_plan, transcript)
  log_lines = _build_log_lines(
    authority,
    session,
    report,
    package_assessment,
    pit_inspection,
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
    authority=authority,
    inspection=inspection,
    device=device,
    pit=pit,
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
    '### Session authority',
    '',
    '- posture: `{posture}`'.format(posture=report.authority.posture),
    '- reviewed phase: `{phase}` ({tone})'.format(
      phase=report.authority.reviewed_phase_label,
      tone=report.authority.reviewed_phase_tone,
    ),
    '- reviewed target label: `{phase}`'.format(
      phase=report.authority.reviewed_target_label,
    ),
    '- live phase: `{phase}` ({tone})'.format(
      phase=report.authority.live_phase_label,
      tone=report.authority.live_phase_tone,
    ),
    '- selected launch path: `{path}`'.format(
      path=report.authority.selected_launch_path_label,
    ),
    '- ownership: `{ownership}`'.format(
      ownership=report.authority.ownership,
    ),
    '- readiness: `{readiness}`'.format(
      readiness=report.authority.readiness,
    ),
    '- fallback active: `{active}`'.format(
      active='yes' if report.authority.fallback_active else 'no',
    ),
    '- summary: {summary}'.format(summary=report.authority.summary),
    '',
    '### Inspection workflow',
    '',
    '- posture: `{posture}`'.format(
      posture=report.inspection.posture,
    ),
    '- detect ran: `{ran}`'.format(
      ran='yes' if report.inspection.detect_ran else 'no',
    ),
    '- info ran: `{ran}`'.format(
      ran='yes' if report.inspection.info_ran else 'no',
    ),
    '- pit ran: `{ran}`'.format(
      ran='yes' if report.inspection.pit_ran else 'no',
    ),
    '- evidence ready: `{ready}`'.format(
      ready='yes' if report.inspection.evidence_ready else 'no',
    ),
    '- read-side only: `{posture}`'.format(
      posture='yes' if report.inspection.read_side_only else 'no',
    ),
    '- summary: {summary}'.format(summary=report.inspection.summary),
    '- next action: {action}'.format(action=report.inspection.next_action),
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
    '- live detection state: `{state}`'.format(
      state=report.device.live.state,
    ),
    '- live source: `{source}`'.format(
      source=report.device.live.source or 'none',
    ),
    '- live fallback posture: `{posture}`'.format(
      posture=report.device.live.fallback_posture,
    ),
    '- live path identity: `{path}` ({ownership})'.format(
      path=report.device.live.path_identity.path_label,
      ownership=report.device.live.path_identity.ownership,
    ),
    '- live delegated label: `{label}`'.format(
      label=report.device.live.path_identity.delegated_path_label,
    ),
    '- live identity confidence: `{confidence}`'.format(
      confidence=report.device.live.path_identity.identity_confidence,
    ),
    '- live info state: `{state}`'.format(
      state=report.device.live.info_state,
    ),
    '- live summary: {summary}'.format(
      summary=report.device.live.summary,
    ),
    '- live path summary: {summary}'.format(
      summary=report.device.live.path_identity.summary,
    ),
    '',
    '### PIT inspection',
    '',
    '- state: `{state}`'.format(state=report.pit.state),
    '- source: `{source}`'.format(source=report.pit.source or 'none'),
    '- fallback posture: `{posture}`'.format(
      posture=report.pit.fallback_posture,
    ),
    '- package alignment: `{alignment}`'.format(
      alignment=report.pit.package_alignment,
    ),
    '- device alignment: `{alignment}`'.format(
      alignment=report.pit.device_alignment,
    ),
    '- observed fingerprint: `{fingerprint}`'.format(
      fingerprint=report.pit.observed_pit_fingerprint or 'unknown',
    ),
    '- reviewed fingerprint: `{fingerprint}`'.format(
      fingerprint=report.pit.reviewed_pit_fingerprint or 'unknown',
    ),
    '- partition rows: `{count}`'.format(count=report.pit.entry_count),
    '- summary: {summary}'.format(summary=report.pit.summary),
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
  if report.authority.block_reason:
    lines.append('- authority block reason: {reason}'.format(
      reason=report.authority.block_reason,
    ))
  if report.authority.refresh_reason:
    lines.append('- authority refresh: {reason}'.format(
      reason=report.authority.refresh_reason,
    ))
  for boundary in report.inspection.action_boundaries:
    lines.append('- inspection boundary: {boundary}'.format(
      boundary=boundary,
    ))
  for note in report.inspection.notes[:2]:
    lines.append('- inspection note: {note}'.format(note=note))
  if report.device.live.source_labels:
    lines.append('- live sources considered: `{sources}`'.format(
      sources=', '.join(report.device.live.source_labels),
    ))
  if report.device.live.path_identity.operator_guidance:
    lines.append('- live path guidance: {guidance}'.format(
      guidance=report.device.live.path_identity.operator_guidance[0],
    ))
  if report.device.live.device_present:
    lines.append('- live serial: `{serial}`'.format(
      serial=report.device.live.serial or 'unknown',
    ))
    lines.append('- live support posture: `{posture}`'.format(
      posture=report.device.live.support_posture,
    ))
    lines.append('- live product code: `{product}`'.format(
      product=report.device.live.product_code or 'unknown',
    ))
    lines.append('- live canonical product code: `{product}`'.format(
      product=report.device.live.canonical_product_code or 'unknown',
    ))
    lines.append('- live marketing name: `{name}`'.format(
      name=report.device.live.marketing_name or 'unknown',
    ))
    lines.append('- live mode: `{mode}`'.format(
      mode=report.device.live.mode or 'unknown',
    ))
    lines.append('- live manufacturer: `{name}`'.format(
      name=report.device.live.manufacturer or 'unknown',
    ))
    lines.append('- live android version: `{version}`'.format(
      version=report.device.live.android_version or 'unknown',
    ))
    lines.append('- live security patch: `{patch}`'.format(
      patch=report.device.live.security_patch or 'unknown',
    ))
    lines.append('- live bootloader: `{bootloader}`'.format(
      bootloader=report.device.live.bootloader_version or 'unknown',
    ))
    if report.device.live.capability_hints:
      lines.append('- live capability hints: `{hints}`'.format(
        hints=', '.join(report.device.live.capability_hints),
      ))
    if report.device.live.operator_guidance:
      lines.append('- live guidance: {guidance}'.format(
        guidance=report.device.live.operator_guidance[0],
      ))
  if report.device.mode_entry_instructions:
    lines.append('- mode entry: {instruction}'.format(
      instruction=report.device.mode_entry_instructions[0],
    ))
  if report.pit.partition_names:
    lines.append('- pit partitions: `{partitions}`'.format(
      partitions=', '.join(report.pit.partition_names),
    ))
  if report.pit.download_path:
    lines.append('- pit download path: `{path}`'.format(
      path=report.pit.download_path,
    ))
  for guidance in report.pit.operator_guidance[:2]:
    lines.append('- pit guidance: {guidance}'.format(guidance=guidance))
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
    fallback_name = output_path.stem + '.transport.log'
    reference_name = _safe_reference_file_name(
      report.transcript.reference_file_name,
      fallback_name=fallback_name,
    )
    transcript_path = output_path.parent / (
      reference_name
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


def _build_inspection_evidence(
  session: PlatformSession,
) -> InspectionWorkflowEvidence:
  inspection = session.inspection
  return InspectionWorkflowEvidence(
    posture=inspection.posture.value,
    summary=inspection.summary,
    detect_ran=inspection.detect_ran,
    info_ran=inspection.info_ran,
    pit_ran=inspection.pit_ran,
    evidence_ready=inspection.evidence_ready,
    next_action=inspection.next_action,
    action_boundaries=inspection.action_boundaries,
    notes=inspection.notes,
    captured_at_utc=inspection.captured_at_utc,
  )


def _build_session_authority_evidence(
  session: PlatformSession,
  preflight_report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  pit_inspection: Optional[PitInspection],
  pit_required_for_safe_path: bool = False,
) -> SessionAuthorityEvidence:
  """Build the exported session-authority evidence surface."""

  authority = build_session_authority_snapshot(
    session,
    preflight_report=preflight_report,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  return SessionAuthorityEvidence(
    schema_version=authority.schema_version,
    posture=authority.posture.value,
    reviewed_phase=authority.reviewed_phase,
    reviewed_phase_label=authority.reviewed_phase_label,
    reviewed_target_label=authority.reviewed_target_label,
    reviewed_phase_tone=authority.reviewed_phase_tone,
    live_phase_label=authority.live_phase_label,
    live_phase_tone=authority.live_phase_tone,
    selected_launch_path=authority.selected_launch_path.value,
    selected_launch_path_label=authority.selected_launch_path_label,
    ownership=authority.ownership.value,
    readiness=authority.readiness.value,
    fallback_active=authority.fallback_active,
    block_reason=authority.block_reason,
    refresh_state=authority.refresh_state.value,
    refresh_reason=authority.refresh_reason,
    summary=authority.summary,
  )


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


def _build_pit_evidence(
  pit_inspection: Optional[PitInspection],
) -> PitEvidence:
  if pit_inspection is None:
    return PitEvidence(
      schema_version='0.3.0-fs3-04',
      state='not_collected',
      source=None,
      summary='No PIT inspection has been captured yet.',
    )

  return PitEvidence(
    schema_version=pit_inspection.schema_version,
    state=pit_inspection.state.value,
    source=(pit_inspection.source.value if pit_inspection.source is not None else None),
    summary=pit_inspection.summary,
    fallback_posture=pit_inspection.fallback_posture.value,
    fallback_reason=pit_inspection.fallback_reason,
    observed_product_code=pit_inspection.observed_product_code,
    canonical_product_code=pit_inspection.canonical_product_code,
    marketing_name=pit_inspection.marketing_name,
    registry_match_kind=pit_inspection.registry_match_kind,
    observed_pit_fingerprint=pit_inspection.observed_pit_fingerprint,
    reviewed_pit_fingerprint=pit_inspection.reviewed_pit_fingerprint,
    package_alignment=pit_inspection.package_alignment.value,
    device_alignment=pit_inspection.device_alignment.value,
    download_path=pit_inspection.download_path,
    entry_count=pit_inspection.entry_count,
    partition_names=pit_inspection.partition_names,
    notes=pit_inspection.notes,
    operator_guidance=pit_inspection.operator_guidance,
  )


def _build_live_device_evidence(
  session: PlatformSession,
) -> LiveDeviceEvidence:
  live_detection = session.live_detection
  snapshot = live_detection.snapshot
  return LiveDeviceEvidence(
    state=live_detection.state.value,
    summary=live_detection.summary,
    source=(
      live_detection.source.value
      if live_detection.source is not None
      else None
    ),
    path_identity=_build_live_path_identity_evidence(session),
    source_labels=live_detection.source_labels,
    fallback_posture=live_detection.fallback_posture.value,
    fallback_reason=live_detection.fallback_reason,
    device_present=live_detection.device_present,
    command_ready=live_detection.command_ready,
    support_posture=(
      snapshot.support_posture.value
      if snapshot is not None
      else 'identity_incomplete'
    ),
    serial=snapshot.serial if snapshot is not None else None,
    transport=snapshot.transport if snapshot is not None else None,
    product_code=snapshot.product_code if snapshot is not None else None,
    canonical_product_code=(
      snapshot.canonical_product_code
      if snapshot is not None
      else None
    ),
    marketing_name=snapshot.marketing_name if snapshot is not None else None,
    registry_match_kind=(
      snapshot.registry_match_kind
      if snapshot is not None
      else 'unknown'
    ),
    mode=snapshot.mode if snapshot is not None else None,
    info_state=(
      snapshot.info_state.value
      if snapshot is not None
      else 'not_collected'
    ),
    info_source_label=snapshot.info_source_label if snapshot is not None else None,
    manufacturer=snapshot.manufacturer if snapshot is not None else None,
    brand=snapshot.brand if snapshot is not None else None,
    android_version=snapshot.android_version if snapshot is not None else None,
    build_id=snapshot.build_id if snapshot is not None else None,
    security_patch=snapshot.security_patch if snapshot is not None else None,
    build_fingerprint=(
      snapshot.build_fingerprint if snapshot is not None else None
    ),
    bootloader_version=(
      snapshot.bootloader_version if snapshot is not None else None
    ),
    build_tags=snapshot.build_tags if snapshot is not None else None,
    capability_hints=snapshot.capability_hints if snapshot is not None else (),
    operator_guidance=snapshot.operator_guidance if snapshot is not None else (),
    notes=live_detection.notes,
  )


def _build_live_path_identity_evidence(
  session: PlatformSession,
) -> LivePathIdentityEvidence:
  """Build the exported live-path identity surface."""

  path_identity = session.live_detection.path_identity
  return LivePathIdentityEvidence(
    schema_version=path_identity.schema_version,
    ownership=path_identity.ownership.value,
    path_label=path_identity.path_label,
    delegated_path_label=path_identity.delegated_path_label,
    mode_label=path_identity.mode_label,
    identity_confidence=path_identity.identity_confidence.value,
    summary=path_identity.summary,
    operator_guidance=path_identity.operator_guidance,
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
  if session.inspection.posture == InspectionWorkflowPosture.READY:
    return 'inspection_ready'
  if session.inspection.posture == InspectionWorkflowPosture.PARTIAL:
    return 'inspection_partial'
  if session.inspection.posture == InspectionWorkflowPosture.FAILED:
    return 'inspection_failed'
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
    session.inspection.evidence_ready
    or
    session.last_event is not None
    or session.guards.has_device
    or session.guards.package_loaded
    or session.live_detection.state != LiveDetectionState.UNHYDRATED
  )


def _next_action(
  session: PlatformSession,
  report: PreflightReport,
  flash_plan: FlashPlanEvidence,
  authority: SessionAuthorityEvidence,
  pit_inspection: Optional[PitInspection],
  transport_trace: Optional[HeimdallNormalizedTrace],
) -> str:
  if session.phase == SessionPhase.RESUME_NEEDED or (
    transport_trace is not None
    and transport_trace.state == HeimdallTraceState.RESUME_NEEDED
  ):
    return 'Complete the manual recovery step, then use Continue after recovery before exporting final evidence.'
  if session.phase == SessionPhase.COMPLETED:
    return 'Export evidence and the bounded transport transcript for closeout review.'
  if session.phase == SessionPhase.FAILED:
    return 'Export evidence, review the failure transcript, and only then decide whether to retry.'
  if session.inspection.posture != InspectionWorkflowPosture.UNINSPECTED:
    return session.inspection.next_action
  if session.live_detection.state == LiveDetectionState.UNHYDRATED:
    return 'Run Detect device to establish current Samsung mode and live identity.'
  if _pit_read_is_next(session, pit_inspection):
    return 'Run Read PIT to capture bounded partition truth before widening package or execute claims.'
  if flash_plan.package_id == 'awaiting-package':
    return 'Load a reviewed package before bounded safe-path planning can continue.'
  if report.gate == report.gate.BLOCKED:
    return report.recommended_action
  if report.gate == report.gate.WARN:
    return 'Resolve or acknowledge warning findings before the bounded safe-path lane can open.'
  if not flash_plan.ready_for_transport:
    return 'Resolve the reviewed flash-plan blockers before any transport command is generated.'
  if session.phase == SessionPhase.READY_TO_EXECUTE:
    if flash_plan.suspicious_warning_count:
      return 'Review the bounded flash plan, suspicious-trait warnings, and execute control before transport.'
    return 'Review the bounded flash plan, recovery guidance, and execute control before transport.'
  if authority.readiness == 'narrowed':
    return 'Keep the current safe-path claim narrow until live, PIT, or package truth becomes explicit enough to proceed.'
  if _export_ready(session):
    return 'Export evidence for the current review state or continue the next bounded step.'
  return 'Continue the fixture-driven review path and preserve the evidence trail.'


def _pit_read_is_next(
  session: PlatformSession,
  pit_inspection: Optional[PitInspection],
) -> bool:
  """Return whether bounded PIT capture is the next honest deck step."""

  snapshot = session.live_detection.snapshot
  if snapshot is None or not snapshot.command_ready:
    return False
  if snapshot.source.value not in ('usb', 'heimdall'):
    return False
  if pit_inspection is None:
    return True
  if pit_inspection.state != PitInspectionState.CAPTURED:
    return True
  return pit_inspection.device_alignment == PitDeviceAlignment.NOT_PROVIDED


def _summary_for_session(
  session: PlatformSession,
  report: PreflightReport,
  outcome: OutcomeEvidence,
  flash_plan: FlashPlanEvidence,
  transcript: TranscriptEvidence,
) -> str:
  if session.inspection.posture != InspectionWorkflowPosture.UNINSPECTED:
    return session.inspection.summary
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
  authority: SessionAuthorityEvidence,
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  pit_inspection: Optional[PitInspection],
  transport_trace: Optional[HeimdallNormalizedTrace],
  reviewed_flash_plan: Optional[ReviewedFlashPlan],
) -> Tuple[str, ...]:
  guidance = []
  device_resolution = resolve_device_profile(session.product_code)
  path_identity = session.live_detection.path_identity
  if authority.block_reason is not None:
    guidance.append(authority.block_reason)
  if authority.refresh_reason is not None:
    guidance.append(authority.refresh_reason)
  if (
    path_identity.ownership.value in ('delegated', 'fallback')
    and path_identity.operator_guidance
  ):
    guidance.append(path_identity.operator_guidance[0])
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

  if pit_inspection is not None:
    if pit_inspection.state in (
      PitInspectionState.MALFORMED,
      PitInspectionState.FAILED,
    ):
      guidance.append('Do not treat the current PIT inspection as trustworthy until the PIT parser and acquisition path are healthy again.')
    elif pit_inspection.device_alignment == PitDeviceAlignment.MISMATCHED:
      guidance.append('Do not proceed until the observed PIT product code agrees with the current session device identity.')
    elif pit_inspection.package_alignment == PitPackageAlignment.MISMATCHED:
      guidance.append('Do not proceed until the reviewed package PIT fingerprint matches the observed device PIT.')
    elif pit_inspection.state == PitInspectionState.PARTIAL:
      guidance.append('Keep PIT review bounded until metadata and partition rows agree fully.')
    guidance.extend(pit_inspection.operator_guidance[:1])

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
  authority: SessionAuthorityEvidence,
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  pit_inspection: Optional[PitInspection],
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
      source='authority',
      label='Launch path authority',
      summary=authority.summary,
      severity=_authority_severity(authority),
    ),
    DecisionTraceEntry(
      source='preflight',
      label='Trust gate',
      summary=report.summary,
      severity=report.gate.value,
    ),
  ]

  if session.inspection.posture != InspectionWorkflowPosture.UNINSPECTED:
    inspection_severity = 'info'
    if session.inspection.posture == InspectionWorkflowPosture.READY:
      inspection_severity = 'success'
    elif session.inspection.posture == InspectionWorkflowPosture.PARTIAL:
      inspection_severity = 'warning'
    elif session.inspection.posture == InspectionWorkflowPosture.FAILED:
      inspection_severity = 'danger'
    trace.append(
      DecisionTraceEntry(
        source='inspection',
        label='Inspect-only workflow',
        summary=session.inspection.summary,
        severity=inspection_severity,
      )
    )

  if session.live_detection.state != LiveDetectionState.UNHYDRATED:
    live_severity = 'info'
    if session.live_detection.state == LiveDetectionState.FAILED:
      live_severity = 'danger'
    elif session.live_detection.state == LiveDetectionState.ATTENTION:
      live_severity = 'warning'
    trace.append(
      DecisionTraceEntry(
        source='live_detection',
        label='Live detection',
        summary=session.live_detection.summary,
        severity=live_severity,
      )
    )
    if session.live_detection.path_identity.ownership.value != 'none':
      trace.append(
        DecisionTraceEntry(
          source='live_path',
          label='Live path identity',
          summary=session.live_detection.path_identity.summary,
          severity=_live_path_severity(session.live_detection.path_identity),
        )
      )
    if (
      session.live_detection.snapshot is not None
      and session.live_detection.snapshot.info_state != LiveDeviceInfoState.NOT_COLLECTED
    ):
      info_severity = 'info'
      if session.live_detection.snapshot.info_state == LiveDeviceInfoState.FAILED:
        info_severity = 'danger'
      elif session.live_detection.snapshot.info_state == LiveDeviceInfoState.PARTIAL:
        info_severity = 'warning'
      trace.append(
        DecisionTraceEntry(
          source='live_info',
          label='Live info snapshot',
          summary='Live info posture is {state}.'.format(
            state=session.live_detection.snapshot.info_state.value,
          ),
          severity=info_severity,
        )
      )

  if pit_inspection is not None:
    pit_severity = 'info'
    if pit_inspection.state in (
      PitInspectionState.MALFORMED,
      PitInspectionState.FAILED,
    ):
      pit_severity = 'danger'
    elif pit_inspection.device_alignment == PitDeviceAlignment.MISMATCHED:
      pit_severity = 'danger'
    elif pit_inspection.package_alignment == PitPackageAlignment.MISMATCHED:
      pit_severity = 'danger'
    elif pit_inspection.state == PitInspectionState.PARTIAL:
      pit_severity = 'warning'
    elif pit_inspection.device_alignment == PitDeviceAlignment.NOT_PROVIDED:
      pit_severity = 'warning'
    elif pit_inspection.package_alignment in (
      PitPackageAlignment.MISSING_REVIEWED,
      PitPackageAlignment.MISSING_OBSERVED,
    ):
      pit_severity = 'warning'
    elif pit_inspection.package_alignment == PitPackageAlignment.MATCHED:
      pit_severity = 'success'
    trace.append(
      DecisionTraceEntry(
        source='pit',
        label='PIT inspection',
        summary=pit_inspection.summary,
        severity=pit_severity,
      )
    )
    if pit_inspection.package_alignment == PitPackageAlignment.MISMATCHED:
      trace.append(
        DecisionTraceEntry(
          source='pit',
          label='PIT/package alignment',
          summary='Observed PIT fingerprint does not match the reviewed package fingerprint.',
          severity='danger',
        )
      )
    if pit_inspection.device_alignment == PitDeviceAlignment.MISMATCHED:
      trace.append(
        DecisionTraceEntry(
          source='pit',
          label='PIT/device alignment',
          summary='Observed PIT product code does not match the current session device identity.',
          severity='danger',
        )
      )

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
  authority: SessionAuthorityEvidence,
  session: PlatformSession,
  report: PreflightReport,
  package_assessment: Optional[PackageManifestAssessment],
  pit_inspection: Optional[PitInspection],
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
    '[AUTHORITY] posture={posture} path={path} ownership={ownership} readiness={readiness} fallback={fallback}'.format(
      posture=authority.posture,
      path=authority.selected_launch_path,
      ownership=authority.ownership,
      readiness=authority.readiness,
      fallback='yes' if authority.fallback_active else 'no',
    ),
    '[AUTHORITY-SUMMARY] {summary}'.format(summary=authority.summary),
    '[PHASE] {phase}'.format(phase=session.phase.value),
    '[GATE] {gate}'.format(gate=report.gate.value),
    '[DEVICE] {device}'.format(device=session.product_code or 'Awaiting device'),
    '[PACKAGE] {package}'.format(package=session.package_id or 'Awaiting package'),
  ]
  if authority.block_reason is not None:
    lines.append('[AUTHORITY-BLOCK] {reason}'.format(reason=authority.block_reason))
  if authority.refresh_reason is not None:
    lines.append('[AUTHORITY-REFRESH] {reason}'.format(reason=authority.refresh_reason))
  if session.guards.has_device:
    lines.append(
      '[DEVICE-REGISTRY] match={match} canonical={canonical} name={name}'.format(
        match=device_resolution.match_kind.value,
        canonical=device_resolution.canonical_product_code or 'unknown',
        name=device_resolution.marketing_name or 'unknown',
      )
    )
  if session.live_detection.state != LiveDetectionState.UNHYDRATED:
    lines.append(
      '[LIVE-DETECT] state={state} source={source} fallback={fallback}'.format(
        state=session.live_detection.state.value,
        source=(
          session.live_detection.source.value
          if session.live_detection.source is not None
          else 'none'
        ),
        fallback=session.live_detection.fallback_posture.value,
      )
    )
    lines.append('[LIVE-SUMMARY] {summary}'.format(
      summary=session.live_detection.summary,
    ))
    lines.append(
      '[LIVE-PATH] ownership={ownership} label="{label}" delegated="{delegated}" confidence={confidence}'.format(
        ownership=session.live_detection.path_identity.ownership.value,
        label=session.live_detection.path_identity.path_label,
        delegated=session.live_detection.path_identity.delegated_path_label,
        confidence=session.live_detection.path_identity.identity_confidence.value,
      )
    )
    if session.live_detection.path_identity.operator_guidance:
      lines.append(
        '[LIVE-PATH-GUIDANCE] {guidance}'.format(
          guidance=session.live_detection.path_identity.operator_guidance[0],
        )
      )
    if session.live_detection.snapshot is not None:
      lines.append(
        '[LIVE-IDENTITY] serial={serial} product={product} mode={mode} support={support}'.format(
          serial=session.live_detection.snapshot.serial,
          product=session.live_detection.snapshot.product_code or 'unknown',
          mode=session.live_detection.snapshot.mode,
          support=session.live_detection.snapshot.support_posture.value,
        )
      )
      lines.append(
        '[LIVE-INFO] posture={state} manufacturer={manufacturer} android={android} security_patch={patch}'.format(
          state=session.live_detection.snapshot.info_state.value,
          manufacturer=session.live_detection.snapshot.manufacturer or 'unknown',
          android=session.live_detection.snapshot.android_version or 'unknown',
          patch=session.live_detection.snapshot.security_patch or 'unknown',
        )
      )
  if session.inspection.posture != InspectionWorkflowPosture.UNINSPECTED:
    lines.append(
      '[INSPECTION] posture={posture} detect_ran={detect_ran} info_ran={info_ran} pit_ran={pit_ran} evidence_ready={ready}'.format(
        posture=session.inspection.posture.value,
        detect_ran='yes' if session.inspection.detect_ran else 'no',
        info_ran='yes' if session.inspection.info_ran else 'no',
        pit_ran='yes' if session.inspection.pit_ran else 'no',
        ready='yes' if session.inspection.evidence_ready else 'no',
      )
    )
    lines.append('[INSPECTION-SUMMARY] {summary}'.format(
      summary=session.inspection.summary,
    ))
    lines.append('[INSPECTION-NEXT] {action}'.format(
      action=session.inspection.next_action,
    ))
    for boundary in session.inspection.action_boundaries[:1]:
      lines.append('[INSPECTION-BOUNDARY] {boundary}'.format(
        boundary=boundary,
      ))

  if pit_inspection is not None:
    lines.append(
      '[PIT] state={state} source={source} entries={entries} package_alignment={package_alignment} device_alignment={device_alignment}'.format(
        state=pit_inspection.state.value,
        source=(pit_inspection.source.value if pit_inspection.source is not None else 'none'),
        entries=pit_inspection.entry_count,
        package_alignment=pit_inspection.package_alignment.value,
        device_alignment=pit_inspection.device_alignment.value,
      )
    )
    lines.append('[PIT-SUMMARY] {summary}'.format(summary=pit_inspection.summary))
    if pit_inspection.observed_pit_fingerprint is not None:
      lines.append(
        '[PIT-FINGERPRINT] observed={observed} reviewed={reviewed}'.format(
          observed=pit_inspection.observed_pit_fingerprint,
          reviewed=pit_inspection.reviewed_pit_fingerprint or 'unknown',
        )
      )
    if pit_inspection.partition_names:
      lines.append(
        '[PIT-PARTITIONS] {partitions}'.format(
          partitions=', '.join(pit_inspection.partition_names),
        )
      )
    for guidance in pit_inspection.operator_guidance[:1]:
      lines.append('[PIT-GUIDANCE] {guidance}'.format(guidance=guidance))

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
    if transport_trace.command_plan.capability.value == 'flash_package':
      lines.append(
        '[SAFE-PATH] governance=platform_supervised lane=bounded_reviewed_flash_session lower_transport=heimdall'.format()
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


def _authority_severity(authority: SessionAuthorityEvidence) -> str:
  if authority.readiness == 'blocked':
    return 'danger'
  if authority.readiness == 'narrowed':
    return 'warning'
  if authority.readiness == 'ready':
    return 'success'
  return 'info'


def _live_path_severity(path_identity: object) -> str:
  """Return one severity tier for the current live-path identity."""

  ownership = getattr(getattr(path_identity, 'ownership', None), 'value', 'none')
  confidence = getattr(
    getattr(path_identity, 'identity_confidence', None),
    'value',
    'unavailable',
  )
  if ownership == 'fallback':
    return 'warning'
  if ownership == 'delegated' and confidence in ('serial_only', 'unavailable'):
    return 'warning'
  if ownership == 'native' and confidence == 'profiled':
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
  scenario_slug = _safe_file_component(
    scenario_name.lower().replace(' ', '-'),
    fallback='scenario',
  )
  return 'cv-{stamp}-{phase}-{scenario}'.format(
    stamp=normalized,
    phase=_safe_file_component(session.phase.value, fallback='phase'),
    scenario=scenario_slug,
  )


def _dedupe_strings(values: Iterable[str]) -> Tuple[str, ...]:
  deduped = []
  for value in values:
    if value not in deduped:
      deduped.append(value)
  return tuple(deduped)


def _safe_reference_file_name(
  reference_file_name: Optional[str],
  fallback_name: str,
) -> str:
  candidate = reference_file_name or fallback_name
  last_segment = candidate.replace('\\', '/').split('/')[-1]
  safe_name = _safe_file_component(last_segment, fallback=fallback_name)
  return safe_name


def _safe_file_component(value: str, fallback: str = 'artifact') -> str:
  candidate = str(value or '').strip()
  if not candidate:
    return fallback
  candidate = candidate.replace('\\', '-').replace('/', '-')
  candidate = SAFE_FILE_COMPONENT_PATTERN.sub('-', candidate)
  candidate = SAFE_DOT_RUN_PATTERN.sub('-', candidate)
  candidate = candidate.strip(' .-_')
  if not candidate:
    return fallback
  return candidate
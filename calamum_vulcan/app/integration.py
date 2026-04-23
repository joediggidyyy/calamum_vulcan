"""Integrated closeout walkthrough helpers for Calamum Vulcan release lanes."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import replace
from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
from typing import Optional
from typing import Tuple

from calamum_vulcan.adapters.adb_fastboot import AndroidToolsBackend
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsOperation
from calamum_vulcan.adapters.adb_fastboot import AndroidToolsProcessResult
from calamum_vulcan.adapters.adb_fastboot import build_adb_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_adb_device_info_command_plan
from calamum_vulcan.adapters.adb_fastboot import build_fastboot_detect_command_plan
from calamum_vulcan.adapters.adb_fastboot import normalize_android_tools_result
from calamum_vulcan.adapters.heimdall import build_print_pit_command_plan
from calamum_vulcan.adapters.heimdall import normalize_heimdall_result
from calamum_vulcan.domain.reporting import REPORT_EXPORT_TARGETS
from calamum_vulcan.domain.reporting import REPORT_SCHEMA_VERSION
from calamum_vulcan.domain.reporting import SessionEvidenceReport
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.domain.live_device import LiveFallbackPosture
from calamum_vulcan.domain.live_device import apply_live_device_info_trace
from calamum_vulcan.domain.live_device import build_live_detection_session
from calamum_vulcan.domain.live_device import build_usb_live_detection_session
from calamum_vulcan.domain.pit import build_pit_inspection
from calamum_vulcan.domain.safe_path import SAFE_PATH_CLOSE_SUITE_NAME
from calamum_vulcan.domain.state import PlatformSession
from calamum_vulcan.domain.state import build_inspection_workflow
from calamum_vulcan.fixtures import load_heimdall_pit_fixture
from calamum_vulcan.usb import USBDeviceDescriptor
from calamum_vulcan.usb import USBProbeResult

from .demo import build_demo_adapter_session
from .demo import build_demo_package_assessment
from .demo import build_demo_pit_inspection
from .demo import build_demo_session
from .demo import scenario_label
from .view_models import PANEL_TITLES
from .view_models import build_shell_view_model
from .view_models import describe_shell


INTEGRATION_SUITE_NAMES = (
  'sprint-close',
  'orchestration-close',
  'read-side-close',
  SAFE_PATH_CLOSE_SUITE_NAME,
)

PLANNED_INTEGRATION_SUITE_NAMES = ()

SPRINT_CLOSE_CARRY_FORWARD_DEBT = (
  'Keep live-device subprocess transport out of `0.1.0`; the next release should define the first bounded runtime session loop explicitly.',
  'Decide which transport artifacts should graduate from summarized evidence into preserved transcript files in `0.2.0`.',
  'Promote PIT-oriented adapter capabilities into operator-driven shell controls only after the current shell contract stays stable under live transport.',
  'Close the Qt deployment/font-packaging debt before broader distribution or screenshot-heavy release review.',
)

ORCHESTRATION_CLOSE_CARRY_FORWARD_DEBT = (
  'Decide whether bounded Heimdall subprocess execution should stay lab-only in `0.3.0` or graduate into a more explicit operator control surface.',
  'Promote transcript packaging beyond plain transport logs only after redaction, PIT handling, and evidence-volume policy stay explicit.',
  'Decide whether future runtime lanes should bind live PIT/device interrogation into reviewed-plan truth or keep those concerns separated.',
  'Keep GUI startup detection explicit and user-invoked until any background probing can prove it stays off the UI thread.',
)

READ_SIDE_CLOSE_CARRY_FORWARD_DEBT = (
  'Expand the repo-owned device registry and PIT fixture corpus before widening native read-side support claims beyond the current reviewed Samsung subset.',
  'Decide whether fastboot-detected fallback sessions should gain any richer repo-owned identity beyond the current bounded labeling and guidance surface.',
  'Decide how much PIT/package alignment truth should graduate from evidence and guidance into harder runtime/preflight enforcement in `0.4.0`.',
  'Keep detached GUI host runtime hygiene under observation as live read-side coverage expands; no fresh orphan was observed in the latest closeout pass.',
)

SAFE_PATH_CLOSE_CARRY_FORWARD_DEBT = (
  'Keep default native transport promotion deferred to `0.5.0`; Heimdall remains the delegated lower transport for the current Samsung subset.',
  'Promote GUI package-load and bounded execute controls only after the new deck contract survives wider operator trials.',
  'Expand real-hardware Heimdall detect fixtures so normalization coverage keeps pace with reviewed Samsung download-mode output variants.',
  'Keep publication rehearsal and any future registry automation out of the historical safe-path-close contract; revisit them only in the active sprint closeout surfaces.',
)


@dataclass(frozen=True)
class SprintCloseProofPoint:
  """One release-close proof requirement with its current status."""

  label: str
  passed: bool
  summary: str


@dataclass(frozen=True)
class SprintCloseScenarioResult:
  """One integrated scenario result captured during the FS-08 review."""

  scenario_id: str
  scenario_name: str
  transport_source: str
  package_fixture: Optional[str]
  phase_label: str
  gate_label: str
  outcome: str
  transport_state: str
  report_id: str
  evidence_summary: str
  next_action: str
  package_id: str
  export_ready: bool
  export_targets: Tuple[str, ...]
  panel_titles: Tuple[str, ...]
  enabled_actions: Tuple[str, ...]
  shell_summary: str
  action_states: Tuple[Tuple[str, str], ...] = ()
  transcript_preserved: bool = False
  transcript_reference_file: Optional[str] = None
  transcript_line_count: int = 0
  transcript_policy: str = 'summary_only'
  inspection_posture: str = 'uninspected'
  inspection_evidence_ready: bool = False
  inspection_read_side_only: bool = True
  live_state: str = 'unhydrated'
  live_source: Optional[str] = None
  live_fallback_posture: str = 'not_needed'
  live_info_state: str = 'not_collected'
  pit_state: str = 'not_collected'
  pit_source: Optional[str] = None
  pit_package_alignment: str = 'not_reviewed'
  pit_fallback_posture: str = 'not_needed'


@dataclass(frozen=True)
class SprintCloseBundle:
  """Structured FS-08 bundle that closes Sprint 0.1.0."""

  schema_version: str
  bundle_id: str
  release_version: str
  suite_name: str
  captured_at_utc: str
  summary: str
  proof_points: Tuple[SprintCloseProofPoint, ...]
  scenarios: Tuple[SprintCloseScenarioResult, ...]
  carry_forward_debt: Tuple[str, ...] = SPRINT_CLOSE_CARRY_FORWARD_DEBT

  def to_dict(self) -> dict:
    """Return a JSON-serializable dictionary for this sprint-close bundle."""

    return asdict(self)


@dataclass(frozen=True)
class _ScenarioSpec:
  """Internal scenario definition used by the sprint-close walkthrough bundle."""

  scenario_id: str
  scenario_name: str
  scenario_key: Optional[str]
  transport_source: str = 'state-fixture'
  package_fixture: Optional[str] = 'scenario-default'
  adapter_fixture: Optional[str] = 'scenario-default'


SPRINT_CLOSE_SCENARIOS = (
  _ScenarioSpec(
    scenario_id='no-device-review',
    scenario_name='No-device shell review',
    scenario_key=None,
    package_fixture=None,
    adapter_fixture=None,
  ),
  _ScenarioSpec(
    scenario_id='happy-path-review',
    scenario_name=scenario_label('happy'),
    scenario_key='happy',
    transport_source='heimdall-adapter',
  ),
  _ScenarioSpec(
    scenario_id='blocked-preflight-review',
    scenario_name=scenario_label('blocked'),
    scenario_key='blocked',
  ),
  _ScenarioSpec(
    scenario_id='incompatible-package-review',
    scenario_name='Incompatible package review',
    scenario_key='ready',
    package_fixture='mismatched',
  ),
  _ScenarioSpec(
    scenario_id='transport-failure-review',
    scenario_name=scenario_label('failure'),
    scenario_key='failure',
    transport_source='heimdall-adapter',
  ),
  _ScenarioSpec(
    scenario_id='resume-handoff-review',
    scenario_name='Resume-handoff adapter review',
    scenario_key='resume',
    transport_source='heimdall-adapter',
  ),
)


def available_integration_suites() -> Tuple[str, ...]:
  """Return supported integrated review bundle names."""

  return INTEGRATION_SUITE_NAMES


def planned_integration_suites() -> Tuple[str, ...]:
  """Return planned-but-not-yet-public integrated review bundle names."""

  return PLANNED_INTEGRATION_SUITE_NAMES


def build_sprint_close_bundle(
  captured_at_utc: Optional[str] = None,
) -> SprintCloseBundle:
  """Build the FS-08 sprint-close walkthrough bundle for Sprint 0.1.0."""

  captured = captured_at_utc or _utc_now()
  scenarios = tuple(
    _build_scenario_result(spec, captured) for spec in SPRINT_CLOSE_SCENARIOS
  )
  proof_points = _build_proof_points(scenarios)
  passed_count = sum(1 for point in proof_points if point.passed)
  summary = (
    'Sprint 0.1.0 closes with {passed}/{total} sprint-close proof points '
    'satisfied across {scenario_count} integrated scenarios.'.format(
      passed=passed_count,
      total=len(proof_points),
      scenario_count=len(scenarios),
    )
  )
  return SprintCloseBundle(
    schema_version=REPORT_SCHEMA_VERSION,
    bundle_id=_bundle_id(captured),
    release_version='0.1.0',
    suite_name='sprint-close',
    captured_at_utc=captured,
    summary=summary,
    proof_points=proof_points,
    scenarios=scenarios,
  )


def build_orchestration_close_bundle(
  captured_at_utc: Optional[str] = None,
) -> SprintCloseBundle:
  """Build the FS2-07 orchestration-close bundle for Sprint 0.2.0."""

  captured = captured_at_utc or _utc_now()
  scenarios = tuple(
    _build_scenario_result(spec, captured) for spec in SPRINT_CLOSE_SCENARIOS
  )
  proof_points = _build_orchestration_proof_points(scenarios)
  passed_count = sum(1 for point in proof_points if point.passed)
  summary = (
    'Sprint 0.2.0 closes with {passed}/{total} orchestration-close proof points '
    'satisfied across {scenario_count} integrated scenarios.'.format(
      passed=passed_count,
      total=len(proof_points),
      scenario_count=len(scenarios),
    )
  )
  return SprintCloseBundle(
    schema_version=REPORT_SCHEMA_VERSION,
    bundle_id=_bundle_id(captured, prefix='cv-fs2-07-orchestration-close'),
    release_version='0.2.0',
    suite_name='orchestration-close',
    captured_at_utc=captured,
    summary=summary,
    proof_points=proof_points,
    scenarios=scenarios,
    carry_forward_debt=ORCHESTRATION_CLOSE_CARRY_FORWARD_DEBT,
  )


def build_read_side_close_bundle(
  captured_at_utc: Optional[str] = None,
) -> SprintCloseBundle:
  """Build the FS3-07 read-side-close bundle for Sprint 0.3.0."""

  captured = captured_at_utc or _utc_now()
  scenarios = _build_read_side_close_scenarios(captured)
  proof_points = _build_read_side_close_proof_points(scenarios)
  passed_count = sum(1 for point in proof_points if point.passed)
  summary = (
    'Sprint 0.3.0 closes with {passed}/{total} read-side-close proof points '
    'satisfied across {scenario_count} integrated scenarios.'.format(
      passed=passed_count,
      total=len(proof_points),
      scenario_count=len(scenarios),
    )
  )
  return SprintCloseBundle(
    schema_version=REPORT_SCHEMA_VERSION,
    bundle_id=_bundle_id(captured, prefix='cv-fs3-07-read-side-close'),
    release_version='0.3.0',
    suite_name='read-side-close',
    captured_at_utc=captured,
    summary=summary,
    proof_points=proof_points,
    scenarios=scenarios,
    carry_forward_debt=READ_SIDE_CLOSE_CARRY_FORWARD_DEBT,
  )


def build_safe_path_close_bundle(
  captured_at_utc: Optional[str] = None,
) -> SprintCloseBundle:
  """Build the FS4-07 safe-path-close bundle for Sprint 0.4.0."""

  captured = captured_at_utc or _utc_now()
  scenarios = _build_safe_path_close_scenarios(captured)
  proof_points = _build_safe_path_close_proof_points(scenarios)
  passed_count = sum(1 for point in proof_points if point.passed)
  summary = (
    'Sprint 0.4.0 closes with {passed}/{total} safe-path-close proof points '
    'satisfied across {scenario_count} integrated scenarios.'.format(
      passed=passed_count,
      total=len(proof_points),
      scenario_count=len(scenarios),
    )
  )
  return SprintCloseBundle(
    schema_version=REPORT_SCHEMA_VERSION,
    bundle_id=_bundle_id(captured, prefix='cv-fs4-07-safe-path-close'),
    release_version='0.4.0',
    suite_name=SAFE_PATH_CLOSE_SUITE_NAME,
    captured_at_utc=captured,
    summary=summary,
    proof_points=proof_points,
    scenarios=scenarios,
    carry_forward_debt=SAFE_PATH_CLOSE_CARRY_FORWARD_DEBT,
  )


def serialize_sprint_close_bundle_json(bundle: SprintCloseBundle) -> str:
  """Render one sprint-close bundle as formatted JSON."""

  return json.dumps(bundle.to_dict(), indent=2, sort_keys=True)


def render_sprint_close_bundle_markdown(bundle: SprintCloseBundle) -> str:
  """Render one sprint-close bundle as a readable Markdown review surface."""

  lines = [
    _bundle_heading(bundle),
    '',
    '- bundle id: `{bundle_id}`'.format(bundle_id=bundle.bundle_id),
    '- captured at: `{captured}`'.format(captured=bundle.captured_at_utc),
    '- release version: `{release}`'.format(release=bundle.release_version),
    '- suite: `{suite}`'.format(suite=bundle.suite_name),
    '',
    '### Summary',
    '',
    bundle.summary,
    '',
    '### Proof points',
    '',
  ]

  for point in bundle.proof_points:
    lines.append(
      '- [{status}] **{label}** — {summary}'.format(
        status='PASS' if point.passed else 'FAIL',
        label=point.label,
        summary=point.summary,
      )
    )

  lines.extend(
    [
      '',
      '### Scenario results',
      '',
      '| Scenario | Source | Phase | Gate | Outcome | Transport | Export | Transcript |',
      '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
  )
  for scenario in bundle.scenarios:
    lines.append(
      '| `{scenario_id}` | `{source}` | `{phase}` | `{gate}` | `{outcome}` | `{transport}` | `{export}` | `{transcript}` |'.format(
        scenario_id=scenario.scenario_id,
        source=scenario.transport_source,
        phase=scenario.phase_label,
        gate=scenario.gate_label,
        outcome=scenario.outcome,
        transport=scenario.transport_state,
        export='ready' if scenario.export_ready else 'not_ready',
        transcript='preserved' if scenario.transcript_preserved else 'summary_only',
      )
    )

  lines.extend(['', '### Scenario notes', ''])
  for scenario in bundle.scenarios:
    lines.extend(
      [
        '#### {name}'.format(name=scenario.scenario_name),
        '',
        '- shell summary: `{summary}`'.format(summary=scenario.shell_summary),
        '- evidence report: `{report_id}`'.format(report_id=scenario.report_id),
        '- next action: {next_action}'.format(next_action=scenario.next_action),
        '- enabled actions: {actions}'.format(
          actions=', '.join(scenario.enabled_actions) or 'none'
        ),
        '- action states: {states}'.format(
          states=', '.join(
            '{label}={state}'.format(label=label, state=state)
            for label, state in scenario.action_states
          ) or 'none'
        ),
        '- transcript: {transcript}'.format(
          transcript=(
            scenario.transcript_reference_file
            if scenario.transcript_reference_file is not None
            else 'summary_only'
          )
        ),
      ]
    )
    if bundle.suite_name == 'read-side-close':
      lines.extend(
        [
          '- inspection posture: `{posture}` (evidence ready: `{ready}`, read-side only: `{read_side_only}`)'.format(
            posture=scenario.inspection_posture,
            ready='yes' if scenario.inspection_evidence_ready else 'no',
            read_side_only='yes' if scenario.inspection_read_side_only else 'no',
          ),
          '- live path: state=`{state}` source=`{source}` info=`{info}` fallback=`{fallback}`'.format(
            state=scenario.live_state,
            source=scenario.live_source or 'none',
            info=scenario.live_info_state,
            fallback=scenario.live_fallback_posture,
          ),
          '- pit path: state=`{state}` source=`{source}` alignment=`{alignment}` fallback=`{fallback}`'.format(
            state=scenario.pit_state,
            source=scenario.pit_source or 'none',
            alignment=scenario.pit_package_alignment,
            fallback=scenario.pit_fallback_posture,
          ),
        ]
      )
    lines.append('')

  lines.extend([_carry_forward_heading(bundle), ''])
  for item in bundle.carry_forward_debt:
    lines.append('- {item}'.format(item=item))

  return '\n'.join(lines)


def write_sprint_close_bundle(
  bundle: SprintCloseBundle,
  output_path: Path,
  format_name: str = 'json',
) -> Path:
  """Write one sprint-close bundle to disk in the requested format."""

  content = serialize_sprint_close_bundle_json(bundle)
  if format_name == 'markdown':
    content = render_sprint_close_bundle_markdown(bundle)
  output_path.parent.mkdir(parents=True, exist_ok=True)
  output_path.write_text(content, encoding='utf-8')
  return output_path


def _build_scenario_result(
  spec: _ScenarioSpec,
  captured_at_utc: str,
) -> SprintCloseScenarioResult:
  session, package_assessment, transport_trace = _resolve_scenario_inputs(spec)
  return _build_scenario_result_from_context(
    scenario_id=spec.scenario_id,
    scenario_name=spec.scenario_name,
    transport_source=spec.transport_source,
    package_fixture=spec.package_fixture,
    captured_at_utc=captured_at_utc,
    session=session,
    package_assessment=package_assessment,
    transport_trace=transport_trace,
  )


def _build_scenario_result_from_context(
  scenario_id: str,
  scenario_name: str,
  transport_source: str,
  package_fixture: Optional[str],
  captured_at_utc: str,
  session: PlatformSession,
  package_assessment: Optional[object] = None,
  pit_inspection: Optional[object] = None,
  transport_trace: Optional[object] = None,
  pit_required_for_safe_path: bool = False,
) -> SprintCloseScenarioResult:
  """Build one integrated scenario result from explicit session context."""

  report = build_session_evidence_report(
    session,
    scenario_name=scenario_name,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    transport_trace=transport_trace,
    captured_at_utc=captured_at_utc,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  model = build_shell_view_model(
    session,
    scenario_name=scenario_name,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    transport_trace=transport_trace,
    session_report=report,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  enabled_actions = tuple(
    action.label for action in model.control_actions if action.visible and action.enabled
  )
  return SprintCloseScenarioResult(
    scenario_id=scenario_id,
    scenario_name=scenario_name,
    transport_source=transport_source,
    package_fixture=package_fixture,
    phase_label=model.phase_label,
    gate_label=model.gate_label,
    outcome=report.outcome.outcome,
    transport_state=report.transport.state,
    report_id=report.report_id,
    evidence_summary=report.summary,
    next_action=report.outcome.next_action,
    package_id=report.package.package_id,
    export_ready=report.outcome.export_ready,
    export_targets=report.host.export_targets,
    panel_titles=tuple(panel.title for panel in model.panels),
    enabled_actions=enabled_actions,
    action_states=tuple(
      (action.label, action.state.value) for action in model.control_actions
    ),
    shell_summary=describe_shell(model),
    transcript_preserved=report.transcript.preserved,
    transcript_reference_file=report.transcript.reference_file_name,
    transcript_line_count=report.transcript.line_count,
    transcript_policy=report.transcript.policy,
    inspection_posture=report.inspection.posture,
    inspection_evidence_ready=report.inspection.evidence_ready,
    inspection_read_side_only=report.inspection.read_side_only,
    live_state=report.device.live.state,
    live_source=report.device.live.source,
    live_fallback_posture=report.device.live.fallback_posture,
    live_info_state=report.device.live.info_state,
    pit_state=report.pit.state,
    pit_source=report.pit.source,
    pit_package_alignment=report.pit.package_alignment,
    pit_fallback_posture=report.pit.fallback_posture,
  )


def _resolve_scenario_inputs(
  spec: _ScenarioSpec,
) -> Tuple[PlatformSession, Optional[object], Optional[object]]:
  if spec.scenario_key is None:
    return PlatformSession(), None, None

  if spec.transport_source == 'heimdall-adapter':
    return build_demo_adapter_session(
      spec.scenario_key,
      package_fixture_name=spec.package_fixture or 'scenario-default',
      adapter_fixture_name=spec.adapter_fixture or 'scenario-default',
    )

  session = build_demo_session(spec.scenario_key)
  package_assessment = None
  if spec.package_fixture is not None:
    package_assessment = build_demo_package_assessment(
      spec.scenario_key,
      session=session,
      package_fixture_name=spec.package_fixture,
    )
  return session, package_assessment, None


def _build_proof_points(
  scenarios: Tuple[SprintCloseScenarioResult, ...],
) -> Tuple[SprintCloseProofPoint, ...]:
  scenario_map = {scenario.scenario_id: scenario for scenario in scenarios}
  no_device = scenario_map['no-device-review']
  happy = scenario_map['happy-path-review']
  blocked = scenario_map['blocked-preflight-review']
  mismatch = scenario_map['incompatible-package-review']
  failure = scenario_map['transport-failure-review']
  resume = scenario_map['resume-handoff-review']

  stable_shell = all(scenario.panel_titles == PANEL_TITLES for scenario in scenarios)
  happy_path_complete = (
    happy.phase_label == 'Completed'
    and happy.gate_label == 'Gate Ready'
    and happy.outcome == 'completed'
    and happy.transport_state == 'completed'
  )
  negative_paths_complete = (
    no_device.gate_label == 'Gate Blocked'
    and blocked.gate_label == 'Gate Blocked'
    and mismatch.gate_label == 'Gate Blocked'
    and failure.outcome == 'failed'
    and failure.transport_state == 'failed'
  )
  evidence_exports_hold = (
    'Export evidence' not in no_device.enabled_actions
    and all(
      'Export evidence' in scenario_map[scenario_id].enabled_actions
      for scenario_id in (
        'happy-path-review',
        'blocked-preflight-review',
        'incompatible-package-review',
        'transport-failure-review',
        'resume-handoff-review',
      )
    )
    and all(
      scenario.export_targets == REPORT_EXPORT_TARGETS
      for scenario in scenarios
    )
  )
  resume_path_normalized = (
    resume.transport_state == 'completed'
    and resume.outcome == 'completed'
    and 'Export evidence' in resume.enabled_actions
  )

  return (
    SprintCloseProofPoint(
      label='Integrated shell contract remains stable across the sprint-close suite',
      passed=stable_shell,
      summary='All integrated scenarios preserve the five-panel shell layout and the control-deck review posture.',
    ),
    SprintCloseProofPoint(
      label='Happy path proves adapter-mediated completion from one product shell',
      passed=happy_path_complete,
      summary='The happy-path walkthrough reaches Completed / Gate Ready with adapter-backed transport normalized as completed.',
    ),
    SprintCloseProofPoint(
      label='Negative-path coverage includes no-device, blocked, mismatch, and transport failure states',
      passed=negative_paths_complete,
      summary='The suite preserves blocked trust-gate behavior for no-device and mismatch conditions while the transport failure lane remains evidence-rich.',
    ),
    SprintCloseProofPoint(
      label='Evidence export stays available on meaningful operator states',
      passed=evidence_exports_hold,
      summary='The empty no-device shell stays intentionally non-exportable, while the review, blocked, mismatch, failure, and resume lanes keep JSON/Markdown export ready.',
    ),
    SprintCloseProofPoint(
      label='Resume and no-reboot recovery stays normalized rather than backend-text-driven',
      passed=resume_path_normalized,
      summary='The resume handoff stays represented as normalized transport evidence with export-ready follow-through.',
    ),
  )


def _build_orchestration_proof_points(
  scenarios: Tuple[SprintCloseScenarioResult, ...],
) -> Tuple[SprintCloseProofPoint, ...]:
  scenario_map = {scenario.scenario_id: scenario for scenario in scenarios}
  no_device = scenario_map['no-device-review']
  happy = scenario_map['happy-path-review']
  blocked = scenario_map['blocked-preflight-review']
  mismatch = scenario_map['incompatible-package-review']
  failure = scenario_map['transport-failure-review']
  resume = scenario_map['resume-handoff-review']

  stable_shell = all(scenario.panel_titles == PANEL_TITLES for scenario in scenarios)
  happy_runtime_complete = (
    happy.phase_label == 'Completed'
    and happy.gate_label == 'Gate Ready'
    and happy.outcome == 'completed'
    and happy.transport_state == 'completed'
    and happy.transcript_preserved
  )
  gated_paths_hold = (
    no_device.gate_label == 'Gate Blocked'
    and blocked.gate_label == 'Gate Blocked'
    and mismatch.gate_label == 'Gate Blocked'
  )
  failure_and_resume_preserve_runtime = (
    failure.outcome == 'failed'
    and failure.transport_state == 'failed'
    and failure.transcript_preserved
    and resume.outcome == 'completed'
    and resume.transport_state == 'completed'
    and resume.transcript_preserved
  )
  transcript_policy_holds = all(
    scenario_map[scenario_id].transcript_policy == 'preserve_bounded_transport_transcript'
    and scenario_map[scenario_id].transcript_line_count > 0
    and scenario_map[scenario_id].transcript_reference_file is not None
    for scenario_id in (
      'happy-path-review',
      'transport-failure-review',
      'resume-handoff-review',
    )
  ) and not any(
    scenario.transcript_preserved
    for scenario in (no_device, blocked, mismatch)
  )

  return (
    SprintCloseProofPoint(
      label='Bounded runtime happy path completes from a reviewed ready state',
      passed=happy_runtime_complete,
      summary='The happy-path runtime lane reaches Completed / Gate Ready and preserves a bounded transport transcript reference.',
    ),
    SprintCloseProofPoint(
      label='Pre-runtime trust gates still block no-device, blocked, and mismatch paths',
      passed=gated_paths_hold,
      summary='No-device, blocked-preflight, and incompatible-package review paths remain blocked before the bounded runtime lane opens.',
    ),
    SprintCloseProofPoint(
      label='Failure and resume runtime paths remain normalized and evidence-rich',
      passed=failure_and_resume_preserve_runtime,
      summary='Failure and no-reboot resume paths stay platform-normalized while preserving transcript references for operator review.',
    ),
    SprintCloseProofPoint(
      label='Transcript promotion stays bounded rather than dumping raw transport into summary-only evidence',
      passed=transcript_policy_holds,
      summary='Only adapter-invoked runtime paths carry preserved transport transcript references; review-only lanes stay summary-only.',
    ),
    SprintCloseProofPoint(
      label='Shell contract remains stable across runtime and review scenarios',
      passed=stable_shell,
      summary='All integrated scenarios preserve the five-panel shell layout and operator-visible contract while runtime ownership increases.',
    ),
  )


def _build_read_side_close_scenarios(
  captured_at_utc: str,
) -> Tuple[SprintCloseScenarioResult, ...]:
  """Return the deterministic FS3-07 read-side closeout scenario matrix."""

  inspect_live_detection = _ready_adb_live_detection()
  inspect_pit = _ready_pit_inspection()
  inspect_session = replace(
    build_demo_session('no-device'),
    live_detection=inspect_live_detection,
    inspection=build_inspection_workflow(
      inspect_live_detection,
      pit_inspection=inspect_pit,
      captured_at_utc=captured_at_utc,
    ),
  )

  native_session = build_demo_session('ready')
  native_package = build_demo_package_assessment('ready', session=native_session)
  native_live_detection = _ready_adb_live_detection()
  native_pit = _ready_pit_inspection(
    detected_product_code=native_session.product_code,
    package_assessment=native_package,
  )
  native_session = replace(
    native_session,
    live_detection=native_live_detection,
    inspection=build_inspection_workflow(
      native_live_detection,
      pit_inspection=native_pit,
      captured_at_utc=captured_at_utc,
    ),
  )

  mismatch_session = build_demo_session('blocked')
  mismatch_package = build_demo_package_assessment(
    'blocked',
    session=mismatch_session,
  )
  mismatch_live_detection = _ready_adb_live_detection()
  mismatch_pit = _ready_pit_inspection(
    detected_product_code=mismatch_session.product_code,
    package_assessment=mismatch_package,
  )
  mismatch_session = replace(
    mismatch_session,
    live_detection=mismatch_live_detection,
    inspection=build_inspection_workflow(
      mismatch_live_detection,
      pit_inspection=mismatch_pit,
      captured_at_utc=captured_at_utc,
    ),
  )

  fastboot_live_detection = _fastboot_fallback_detection(device_present=True)
  fastboot_session = replace(
    build_demo_session('no-device'),
    live_detection=fastboot_live_detection,
    inspection=build_inspection_workflow(
      fastboot_live_detection,
      pit_inspection=None,
      captured_at_utc=captured_at_utc,
    ),
  )

  fallback_exhausted_detection = _fastboot_fallback_detection(device_present=False)
  fallback_exhausted_session = replace(
    build_demo_session('no-device'),
    live_detection=fallback_exhausted_detection,
    inspection=build_inspection_workflow(
      fallback_exhausted_detection,
      pit_inspection=None,
      captured_at_utc=captured_at_utc,
    ),
  )

  return (
    _build_scenario_result_from_context(
      scenario_id='inspect-only-ready-review',
      scenario_name='Inspect-only ready evidence review',
      transport_source='adb-read-side',
      package_fixture=None,
      captured_at_utc=captured_at_utc,
      session=inspect_session,
      package_assessment=None,
      pit_inspection=inspect_pit,
    ),
    _build_scenario_result_from_context(
      scenario_id='native-adb-package-review',
      scenario_name='Native ADB package alignment review',
      transport_source='adb-read-side',
      package_fixture='ready-standard',
      captured_at_utc=captured_at_utc,
      session=native_session,
      package_assessment=native_package,
      pit_inspection=native_pit,
    ),
    _build_scenario_result_from_context(
      scenario_id='pit-mismatch-review',
      scenario_name='PIT mismatch review',
      transport_source='adb-read-side',
      package_fixture='blocked-review',
      captured_at_utc=captured_at_utc,
      session=mismatch_session,
      package_assessment=mismatch_package,
      pit_inspection=mismatch_pit,
    ),
    _build_scenario_result_from_context(
      scenario_id='fastboot-fallback-review',
      scenario_name='Fastboot fallback review',
      transport_source='fastboot-read-side',
      package_fixture=None,
      captured_at_utc=captured_at_utc,
      session=fastboot_session,
      package_assessment=None,
      pit_inspection=None,
    ),
    _build_scenario_result_from_context(
      scenario_id='fallback-exhausted-review',
      scenario_name='Fallback exhausted no-device review',
      transport_source='fastboot-read-side',
      package_fixture=None,
      captured_at_utc=captured_at_utc,
      session=fallback_exhausted_session,
      package_assessment=None,
      pit_inspection=None,
    ),
  )


def _build_safe_path_close_scenarios(
  captured_at_utc: str,
) -> Tuple[SprintCloseScenarioResult, ...]:
  """Return the deterministic FS4-07 safe-path closeout scenario matrix."""

  download_live_detection = _ready_usb_live_detection()

  read_pit_required_session = replace(
    build_demo_session('no-device'),
    live_detection=download_live_detection,
  )

  load_package_pit = _ready_pit_inspection(
    detected_product_code='SM-G991U',
    package_assessment=None,
  )
  load_package_session = replace(
    build_demo_session('no-device'),
    live_detection=download_live_detection,
    inspection=build_inspection_workflow(
      download_live_detection,
      pit_inspection=load_package_pit,
      captured_at_utc=captured_at_utc,
    ),
  )

  ready_session = build_demo_session('ready')
  ready_package = build_demo_package_assessment('ready', session=ready_session)
  ready_pit = build_demo_pit_inspection(
    'ready',
    session=ready_session,
    package_assessment=ready_package,
  )
  ready_session = replace(
    ready_session,
    live_detection=download_live_detection,
    inspection=build_inspection_workflow(
      download_live_detection,
      pit_inspection=ready_pit,
      captured_at_utc=captured_at_utc,
    ),
  )

  runtime_session, runtime_package, runtime_trace = build_demo_adapter_session('ready')
  runtime_pit = build_demo_pit_inspection(
    'ready',
    session=build_demo_session('ready'),
    package_assessment=runtime_package,
  )
  runtime_session = replace(
    runtime_session,
    live_detection=download_live_detection,
    inspection=build_inspection_workflow(
      download_live_detection,
      pit_inspection=runtime_pit,
      captured_at_utc=captured_at_utc,
    ),
  )

  mismatch_session = build_demo_session('blocked')
  mismatch_package = build_demo_package_assessment(
    'blocked',
    session=mismatch_session,
  )
  mismatch_pit = build_demo_pit_inspection(
    'blocked',
    session=mismatch_session,
    package_assessment=mismatch_package,
  )
  mismatch_session = replace(
    mismatch_session,
    live_detection=download_live_detection,
    inspection=build_inspection_workflow(
      download_live_detection,
      pit_inspection=mismatch_pit,
      captured_at_utc=captured_at_utc,
    ),
  )

  fastboot_fallback = _fastboot_fallback_detection(device_present=True)
  fastboot_fallback_session = replace(
    build_demo_session('no-device'),
    live_detection=fastboot_fallback,
    inspection=build_inspection_workflow(
      fastboot_fallback,
      pit_inspection=None,
      captured_at_utc=captured_at_utc,
    ),
  )

  return (
    _build_scenario_result_from_context(
      scenario_id='read-pit-required-review',
      scenario_name='Read PIT required review',
      transport_source='heimdall-read-side',
      package_fixture=None,
      captured_at_utc=captured_at_utc,
      session=read_pit_required_session,
      package_assessment=None,
      pit_inspection=None,
      pit_required_for_safe_path=True,
    ),
    _build_scenario_result_from_context(
      scenario_id='load-package-required-review',
      scenario_name='Load package required review',
      transport_source='heimdall-read-side',
      package_fixture=None,
      captured_at_utc=captured_at_utc,
      session=load_package_session,
      package_assessment=None,
      pit_inspection=load_package_pit,
      pit_required_for_safe_path=True,
    ),
    _build_scenario_result_from_context(
      scenario_id='safe-path-ready-review',
      scenario_name='Bounded safe-path ready review',
      transport_source='state-fixture',
      package_fixture=ready_package.fixture_name,
      captured_at_utc=captured_at_utc,
      session=ready_session,
      package_assessment=ready_package,
      pit_inspection=ready_pit,
      pit_required_for_safe_path=True,
    ),
    _build_scenario_result_from_context(
      scenario_id='safe-path-runtime-complete',
      scenario_name='Bounded safe-path runtime complete',
      transport_source='heimdall-adapter',
      package_fixture=runtime_package.fixture_name,
      captured_at_utc=captured_at_utc,
      session=runtime_session,
      package_assessment=runtime_package,
      pit_inspection=runtime_pit,
      transport_trace=runtime_trace,
      pit_required_for_safe_path=True,
    ),
    _build_scenario_result_from_context(
      scenario_id='pit-mismatch-block-review',
      scenario_name='PIT mismatch block review',
      transport_source='state-fixture',
      package_fixture=mismatch_package.fixture_name,
      captured_at_utc=captured_at_utc,
      session=mismatch_session,
      package_assessment=mismatch_package,
      pit_inspection=mismatch_pit,
      pit_required_for_safe_path=True,
    ),
    _build_scenario_result_from_context(
      scenario_id='fastboot-fallback-boundary-review',
      scenario_name='Fastboot fallback boundary review',
      transport_source='fastboot-read-side',
      package_fixture=None,
      captured_at_utc=captured_at_utc,
      session=fastboot_fallback_session,
      package_assessment=None,
      pit_inspection=None,
      pit_required_for_safe_path=True,
    ),
  )


def _build_read_side_close_proof_points(
  scenarios: Tuple[SprintCloseScenarioResult, ...],
) -> Tuple[SprintCloseProofPoint, ...]:
  """Return proof points for the FS3-07 read-side closeout suite."""

  scenario_map = {scenario.scenario_id: scenario for scenario in scenarios}
  inspect_ready = scenario_map['inspect-only-ready-review']
  native_review = scenario_map['native-adb-package-review']
  pit_mismatch = scenario_map['pit-mismatch-review']
  fastboot_fallback = scenario_map['fastboot-fallback-review']
  fallback_exhausted = scenario_map['fallback-exhausted-review']

  stable_shell = all(scenario.panel_titles == PANEL_TITLES for scenario in scenarios)
  inspect_only_ready = (
    inspect_ready.inspection_posture == 'ready'
    and inspect_ready.inspection_evidence_ready
    and inspect_ready.inspection_read_side_only
    and inspect_ready.transport_state == 'not_invoked'
    and not inspect_ready.transcript_preserved
    and inspect_ready.export_ready
  )
  native_adb_ready = (
    native_review.live_state == 'detected'
    and native_review.live_source == 'adb'
    and native_review.live_info_state == 'captured'
    and native_review.pit_state == 'captured'
    and native_review.pit_package_alignment == 'matched'
    and native_review.gate_label == 'Gate Ready'
  )
  pit_mismatch_visible = (
    pit_mismatch.live_source == 'adb'
    and pit_mismatch.live_info_state == 'captured'
    and pit_mismatch.pit_state == 'captured'
    and pit_mismatch.pit_package_alignment == 'mismatched'
    and pit_mismatch.gate_label == 'Gate Blocked'
  )
  fallback_discipline_visible = (
    fastboot_fallback.live_source == 'fastboot'
    and fastboot_fallback.live_fallback_posture == 'engaged'
    and fastboot_fallback.live_info_state == 'unavailable'
    and fastboot_fallback.inspection_posture == 'partial'
    and fallback_exhausted.live_state == 'cleared'
    and fallback_exhausted.live_fallback_posture == 'engaged'
    and fallback_exhausted.inspection_posture == 'failed'
  )
  export_contract_holds = all(
    scenario.export_targets == REPORT_EXPORT_TARGETS for scenario in scenarios
  ) and all(
    scenario_map[scenario_id].export_ready
    for scenario_id in (
      'inspect-only-ready-review',
      'native-adb-package-review',
      'pit-mismatch-review',
      'fastboot-fallback-review',
      'fallback-exhausted-review',
    )
  )

  return (
    SprintCloseProofPoint(
      label='Inspect-only read-side lane stays evidence-ready without transport activation',
      passed=inspect_only_ready,
      summary='The read-side-ready inspection lane preserves exportable evidence, explicit read-side boundaries, and no transport transcript because no write path was invoked.',
    ),
    SprintCloseProofPoint(
      label='Native ADB detection, bounded info capture, and PIT review remain platform-owned for the supported subset',
      passed=native_adb_ready,
      summary='The native ADB review lane keeps captured live info and captured PIT truth visible while the reviewed package remains Gate Ready with matched alignment.',
    ),
    SprintCloseProofPoint(
      label='Reviewed-package mismatch remains explicit when PIT truth disagrees',
      passed=pit_mismatch_visible,
      summary='The PIT mismatch lane keeps live ADB truth visible while the reviewed package remains blocked by captured mismatched PIT evidence.',
    ),
    SprintCloseProofPoint(
      label='Fallback discipline stays visible when ADB ownership stops at fastboot or no-device states',
      passed=fallback_discipline_visible,
      summary='Fastboot fallback remains visibly engaged when ADB does not establish the device, and the exhausted lane stays explicitly cleared rather than pretending support.',
    ),
    SprintCloseProofPoint(
      label='Shell contract and evidence export targets remain stable across native, fallback, and review-only read-side scenarios',
      passed=stable_shell and export_contract_holds,
      summary='All read-side closeout scenarios preserve the five-panel shell layout and keep JSON/Markdown evidence export targets available for operator review.',
    ),
  )


def _build_safe_path_close_proof_points(
  scenarios: Tuple[SprintCloseScenarioResult, ...],
) -> Tuple[SprintCloseProofPoint, ...]:
  """Return proof points for the FS4-07 safe-path closeout suite."""

  scenario_map = {scenario.scenario_id: scenario for scenario in scenarios}
  read_pit_required = scenario_map['read-pit-required-review']
  load_package_required = scenario_map['load-package-required-review']
  safe_path_ready = scenario_map['safe-path-ready-review']
  runtime_complete = scenario_map['safe-path-runtime-complete']
  pit_mismatch = scenario_map['pit-mismatch-block-review']
  fallback_boundary = scenario_map['fastboot-fallback-boundary-review']

  deck_progression = (
    _action_state(read_pit_required, 'Detect device') == 'completed'
    and _action_state(read_pit_required, 'Read PIT') == 'next'
    and _action_state(read_pit_required, 'Load package') == 'unavailable'
    and _action_state(load_package_required, 'Read PIT') == 'completed'
    and _action_state(load_package_required, 'Load package') == 'next'
    and _action_state(safe_path_ready, 'Load package') == 'completed'
    and _action_state(safe_path_ready, 'Execute flash plan') == 'next'
    and _action_state(runtime_complete, 'Execute flash plan') == 'completed'
    and _action_state(runtime_complete, 'Export evidence') == 'next'
  )
  pit_gating_holds = (
    read_pit_required.gate_label == 'Gate Blocked'
    and safe_path_ready.gate_label == 'Gate Ready'
    and pit_mismatch.gate_label == 'Gate Blocked'
    and _action_state(pit_mismatch, 'Execute flash plan') == 'unavailable'
  )
  delegated_safe_path_holds = (
    safe_path_ready.phase_label == 'Ready to Execute'
    and safe_path_ready.gate_label == 'Gate Ready'
    and safe_path_ready.transport_state == 'not_invoked'
    and safe_path_ready.live_source == 'usb'
    and safe_path_ready.pit_package_alignment == 'matched'
  )
  runtime_evidence_handoff = (
    runtime_complete.transport_state == 'completed'
    and runtime_complete.phase_label == 'Completed'
    and runtime_complete.gate_label == 'Gate Ready'
    and runtime_complete.transcript_preserved
    and _action_state(runtime_complete, 'Export evidence') == 'next'
  )
  fallback_boundaries_hold = (
    fallback_boundary.live_source == 'fastboot'
    and fallback_boundary.live_fallback_posture == 'engaged'
    and _action_state(fallback_boundary, 'Read PIT') == 'unavailable'
    and fallback_boundary.transport_state == 'not_invoked'
  )

  return (
    SprintCloseProofPoint(
      label='The safe-path deck progresses honestly from detect through export',
      passed=deck_progression,
      summary='Integrated scenarios prove Detect device, Read PIT, Load package, Execute flash plan, and Export evidence advance in the documented order without a permanent resume stage.',
    ),
    SprintCloseProofPoint(
      label='Missing or mismatched PIT truth keeps the bounded lane blocked',
      passed=pit_gating_holds,
      summary='Read-PIT-required and PIT-mismatch scenarios stay blocked while the ready review stays Gate Ready only after matched PIT truth is present.',
    ),
    SprintCloseProofPoint(
      label='The ready review now uses native USB for supported-path download-mode identity',
      passed=delegated_safe_path_holds,
      summary='The ready scenario reaches Ready to Execute with native USB explicit for supported-path download-mode identity while PIT and runtime transport remain separately bounded.',
    ),
    SprintCloseProofPoint(
      label='Resolved runtime hands off to exportable evidence and preserved transcript artifacts',
      passed=runtime_evidence_handoff,
      summary='The completed runtime scenario keeps execute marked complete, export marked next, and the bounded transcript preserved for closeout review.',
    ),
    SprintCloseProofPoint(
      label='Fallback boundaries remain explicit when PIT-capable truth is absent',
      passed=fallback_boundaries_hold,
      summary='Fastboot fallback review stays visibly engaged and does not pretend that PIT or bounded safe-path execution is currently available.',
    ),
  )


def _ready_adb_live_detection():
  """Return one deterministic ready ADB live-detection snapshot with info."""

  detection_trace = normalize_android_tools_result(
    build_adb_detect_command_plan(),
    AndroidToolsProcessResult(
      fixture_name='adb-ready',
      operation=AndroidToolsOperation.ADB_DEVICES,
      backend=AndroidToolsBackend.ADB,
      exit_code=0,
      stdout_lines=(
        'List of devices attached',
        'R58N12345AB\tdevice usb:1-1 product:dm3q model:SM_G991U device:dm3q',
      ),
    ),
  )
  info_trace = normalize_android_tools_result(
    build_adb_device_info_command_plan(device_serial='R58N12345AB'),
    AndroidToolsProcessResult(
      fixture_name='adb-info-ready',
      operation=AndroidToolsOperation.ADB_GETPROP,
      backend=AndroidToolsBackend.ADB,
      exit_code=0,
      stdout_lines=(
        '[ro.product.manufacturer]: [samsung]',
        '[ro.product.brand]: [samsung]',
        '[ro.build.version.release]: [14]',
        '[ro.build.version.security_patch]: [2026-04-05]',
        '[ro.bootloader]: [G991USQS9HYD1]',
      ),
    ),
  )
  return apply_live_device_info_trace(
    build_live_detection_session(detection_trace),
    info_trace,
  )


def _ready_usb_live_detection():
  """Return one deterministic native USB download-mode detection snapshot."""

  return build_usb_live_detection_session(
    USBProbeResult(
      state='detected',
      summary='Native USB scan detected a Samsung download-mode device.',
      devices=(
        USBDeviceDescriptor(
          vendor_id=0x04E8,
          product_id=0x685D,
          bus=1,
          address=5,
          serial_number='usb-g991u-lab-01',
          manufacturer='Samsung',
          product_name='Samsung Galaxy S21 (SM-G991U)',
          product_code='SM-G991U',
        ),
      ),
      notes=('Native USB backend resolved from bundled libusb.',),
    ),
    source_labels=('adb', 'fastboot', 'usb'),
  )


def _fastboot_fallback_detection(device_present: bool):
  """Return one deterministic fastboot fallback detection session."""

  stdout_lines = ('R58N12345AB\tfastboot',) if device_present else ()
  fallback_reason = (
    'ADB did not establish a live device; fastboot captured the active companion.'
    if device_present
    else 'ADB did not establish a live device; fastboot fallback also failed to capture a live companion.'
  )
  trace = normalize_android_tools_result(
    build_fastboot_detect_command_plan(),
    AndroidToolsProcessResult(
      fixture_name='fastboot-ready' if device_present else 'fastboot-empty',
      operation=AndroidToolsOperation.FASTBOOT_DEVICES,
      backend=AndroidToolsBackend.FASTBOOT,
      exit_code=0,
      stdout_lines=stdout_lines,
    ),
  )
  return build_live_detection_session(
    trace,
    fallback_posture=LiveFallbackPosture.ENGAGED,
    fallback_reason=fallback_reason,
    source_labels=('adb', 'fastboot'),
  )


def _ready_pit_inspection(
  detected_product_code: Optional[str] = None,
  package_assessment: Optional[object] = None,
):
  """Return one deterministic captured PIT inspection for the read-side suite."""

  trace = normalize_heimdall_result(
    build_print_pit_command_plan(),
    load_heimdall_pit_fixture('pit-print-ready-g991u'),
  )
  return build_pit_inspection(
    trace,
    detected_product_code=detected_product_code,
    package_assessment=package_assessment,
  )


def _bundle_heading(bundle: SprintCloseBundle) -> str:
  if bundle.suite_name == SAFE_PATH_CLOSE_SUITE_NAME:
    return '## Calamum Vulcan FS4-07 safe-path-close bundle'
  if bundle.suite_name == 'read-side-close':
    return '## Calamum Vulcan FS3-07 read-side-close bundle'
  if bundle.suite_name == 'orchestration-close':
    return '## Calamum Vulcan FS2-07 orchestration-close bundle'
  return '## Calamum Vulcan FS-08 sprint-close bundle'


def _carry_forward_heading(bundle: SprintCloseBundle) -> str:
  if bundle.suite_name == SAFE_PATH_CLOSE_SUITE_NAME:
    return '### Carry-forward debt into 0.5.0'
  if bundle.suite_name == 'read-side-close':
    return '### Carry-forward debt into 0.4.0'
  if bundle.suite_name == 'orchestration-close':
    return '### Carry-forward debt into 0.3.0'
  return '### Carry-forward debt into 0.2.0'


def _bundle_id(captured_at_utc: str, prefix: str = 'cv-fs08-sprint-close') -> str:
  stamp = captured_at_utc.replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')
  return '{prefix}-{stamp}'.format(prefix=prefix, stamp=stamp)


def _action_state(
  scenario: SprintCloseScenarioResult,
  label: str,
) -> str:
  """Return the recorded action state for one scenario/control label pair."""

  for action_label, state in scenario.action_states:
    if action_label == label:
      return state
  return 'hidden'


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    '+00:00',
    'Z',
  )
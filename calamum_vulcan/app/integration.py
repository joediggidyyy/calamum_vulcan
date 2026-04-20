"""Integrated sprint-close walkthrough helpers for the Calamum Vulcan FS-08 lane."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
from typing import Optional
from typing import Tuple

from calamum_vulcan.domain.reporting import REPORT_EXPORT_TARGETS
from calamum_vulcan.domain.reporting import REPORT_SCHEMA_VERSION
from calamum_vulcan.domain.reporting import SessionEvidenceReport
from calamum_vulcan.domain.reporting import build_session_evidence_report
from calamum_vulcan.domain.state import PlatformSession

from .demo import build_demo_adapter_session
from .demo import build_demo_package_assessment
from .demo import build_demo_session
from .demo import scenario_label
from .view_models import PANEL_TITLES
from .view_models import build_shell_view_model
from .view_models import describe_shell


INTEGRATION_SUITE_NAMES = ('sprint-close', 'orchestration-close')

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
  transcript_preserved: bool = False
  transcript_reference_file: Optional[str] = None
  transcript_line_count: int = 0
  transcript_policy: str = 'summary_only'


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
        '- transcript: {transcript}'.format(
          transcript=(
            scenario.transcript_reference_file
            if scenario.transcript_reference_file is not None
            else 'summary_only'
          )
        ),
        '',
      ]
    )

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
  report = build_session_evidence_report(
    session,
    scenario_name=spec.scenario_name,
    package_assessment=package_assessment,
    transport_trace=transport_trace,
    captured_at_utc=captured_at_utc,
  )
  model = build_shell_view_model(
    session,
    scenario_name=spec.scenario_name,
    package_assessment=package_assessment,
    transport_trace=transport_trace,
    session_report=report,
  )
  enabled_actions = tuple(
    action.label for action in model.control_actions if action.enabled
  )
  return SprintCloseScenarioResult(
    scenario_id=spec.scenario_id,
    scenario_name=spec.scenario_name,
    transport_source=spec.transport_source,
    package_fixture=spec.package_fixture,
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
    shell_summary=describe_shell(model),
    transcript_preserved=report.transcript.preserved,
    transcript_reference_file=report.transcript.reference_file_name,
    transcript_line_count=report.transcript.line_count,
    transcript_policy=report.transcript.policy,
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


def _bundle_heading(bundle: SprintCloseBundle) -> str:
  if bundle.suite_name == 'orchestration-close':
    return '## Calamum Vulcan FS2-07 orchestration-close bundle'
  return '## Calamum Vulcan FS-08 sprint-close bundle'


def _carry_forward_heading(bundle: SprintCloseBundle) -> str:
  if bundle.suite_name == 'orchestration-close':
    return '### Carry-forward debt into 0.3.0'
  return '### Carry-forward debt into 0.2.0'


def _bundle_id(captured_at_utc: str, prefix: str = 'cv-fs08-sprint-close') -> str:
  stamp = captured_at_utc.replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')
  return '{prefix}-{stamp}'.format(prefix=prefix, stamp=stamp)


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    '+00:00',
    'Z',
  )
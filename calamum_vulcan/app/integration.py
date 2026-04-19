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


INTEGRATION_SUITE_NAMES = ('sprint-close',)

SPRINT_CLOSE_CARRY_FORWARD_DEBT = (
  'Keep live-device subprocess transport out of `0.1.0`; the next release should define the first bounded runtime session loop explicitly.',
  'Decide which transport artifacts should graduate from summarized evidence into preserved transcript files in `0.2.0`.',
  'Promote PIT-oriented adapter capabilities into operator-driven shell controls only after the current shell contract stays stable under live transport.',
  'Close the Qt deployment/font-packaging debt before broader distribution or screenshot-heavy release review.',
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


def serialize_sprint_close_bundle_json(bundle: SprintCloseBundle) -> str:
  """Render one sprint-close bundle as formatted JSON."""

  return json.dumps(bundle.to_dict(), indent=2, sort_keys=True)


def render_sprint_close_bundle_markdown(bundle: SprintCloseBundle) -> str:
  """Render one sprint-close bundle as a readable Markdown review surface."""

  lines = [
    '## Calamum Vulcan FS-08 sprint-close bundle',
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
      '| Scenario | Source | Phase | Gate | Outcome | Transport | Export |',
      '| --- | --- | --- | --- | --- | --- | --- |',
    ]
  )
  for scenario in bundle.scenarios:
    lines.append(
      '| `{scenario_id}` | `{source}` | `{phase}` | `{gate}` | `{outcome}` | `{transport}` | `{export}` |'.format(
        scenario_id=scenario.scenario_id,
        source=scenario.transport_source,
        phase=scenario.phase_label,
        gate=scenario.gate_label,
        outcome=scenario.outcome,
        transport=scenario.transport_state,
        export='ready' if scenario.export_ready else 'not_ready',
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
        '',
      ]
    )

  lines.extend(['### Carry-forward debt into 0.2.0', ''])
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


def _bundle_id(captured_at_utc: str) -> str:
  stamp = captured_at_utc.replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')
  return 'cv-fs08-{stamp}-sprint-close'.format(stamp=stamp)


def _utc_now() -> str:
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    '+00:00',
    'Z',
  )
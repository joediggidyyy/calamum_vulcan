"""Audit current implementation against the planned sprint timeline through 0.5.0."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.app.demo import available_adapter_fixtures
from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_pit_inspection
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.view_models import build_shell_view_model
from calamum_vulcan.domain.state import build_session_authority_snapshot


DEFAULT_OUTPUT_ROOT = REPO_ROOT / 'temp' / 'v050_timeline_audit'
RAW_DIR_NAME = 'raw'
WORKFLOW_PATH = REPO_ROOT / '.github' / 'workflows' / 'python-publish.yml'
DOCS_ROOT = REPO_ROOT / 'docs'
PYPROJECT_PATH = REPO_ROOT / 'pyproject.toml'
README_PATH = REPO_ROOT / 'README.md'
CHANGELOG_PATH = REPO_ROOT / 'CHANGELOG.md'
SPRINT4_EVIDENCE_PATH = DOCS_ROOT / 'Samsung_Android_Flashing_Platform_0.5.0_Execution_Evidence.md'
SPRINT4_READINESS_PLAN_PATH = DOCS_ROOT / 'Samsung_Android_Flashing_Platform_0.5.0_Testing_and_Readiness_Plan.md'
SPRINT4_CHECKLIST_PATH = DOCS_ROOT / 'Samsung_Android_Flashing_Platform_0.5.0_Closeout_and_Prepackage_Checklist.md'
READINESS_SUMMARY_PATH = REPO_ROOT / 'temp' / 'fs5_readiness' / 'readiness_summary.json'
READINESS_SUMMARY_MARKDOWN_PATH = REPO_ROOT / 'temp' / 'fs5_readiness' / 'readiness_summary.md'


SPRINT_LABELS = {
  '0.1.0': 'GUI-first product shell',
  '0.2.0': 'orchestration ownership',
  '0.3.0': 'read-side autonomy',
  '0.5.0': 'session and safe-path extraction',
}


@dataclass(frozen=True)
class CommandCapture:
  """One captured subprocess execution."""

  name: str
  command: Tuple[str, ...]
  returncode: int
  stdout_path: str
  stderr_path: str


@dataclass(frozen=True)
class CriterionResult:
  """One implementation-vs-plan assessment item."""

  sprint: str
  criterion_id: str
  title: str
  status: str
  priority: str
  impact: str
  evidence: Tuple[str, ...]
  next_actions: Tuple[str, ...] = ()
  notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
  """One opportunistic find or notable deviation."""

  finding_id: str
  title: str
  severity: str
  category: str
  summary: str
  evidence: Tuple[str, ...]


@dataclass(frozen=True)
class AuditSummary:
  """Top-level serializable audit summary."""

  captured_at_utc: str
  repo_root: str
  output_root: str
  current_package_version: str
  target_sprint: str
  criteria: Tuple[CriterionResult, ...]
  opportunistic_finds: Tuple[Finding, ...]
  deviations: Tuple[Finding, ...]
  command_captures: Tuple[CommandCapture, ...]
  readiness_status: str
  status_counts: Dict[str, int]
  sprint_counts: Dict[str, Dict[str, int]]
  raw_probe_summary: Dict[str, Any]


def _print(lines: Iterable[str]) -> None:
  for line in lines:
    print(line)


def _ensure_clean_dir(path: Path) -> None:
  if path.exists():
    shutil.rmtree(path)
  path.mkdir(parents=True)


def _read_text(path: Path) -> str:
  return path.read_text(encoding='utf-8')


def _read_json(path: Path) -> Dict[str, Any]:
  return json.loads(path.read_text(encoding='utf-8'))


def _parse_leading_json(text: str) -> Dict[str, Any]:
  stripped = text.lstrip()
  payload, _ = json.JSONDecoder().raw_decode(stripped)
  return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
  path.write_text(
    json.dumps(payload, indent=2, sort_keys=True) + '\n',
    encoding='utf-8',
  )


def _append_progress(path: Path, message: str) -> None:
  with path.open('a', encoding='utf-8') as handle:
    handle.write(message + '\n')


def _status_key(status: str) -> Tuple[int, str]:
  order = {
    'open': 0,
    'partial': 1,
    'implemented': 2,
  }
  return (order.get(status, 99), status)


def _run_command(
  name: str,
  command: Sequence[str],
  raw_root: Path,
  check: bool = True,
) -> Tuple[subprocess.CompletedProcess[str], CommandCapture]:
  stdout_path = raw_root / '{name}.stdout.txt'.format(name=name)
  stderr_path = raw_root / '{name}.stderr.txt'.format(name=name)
  result = subprocess.run(
    command,
    cwd=REPO_ROOT,
    capture_output=True,
    text=True,
  )
  stdout_path.write_text(result.stdout, encoding='utf-8')
  stderr_path.write_text(result.stderr, encoding='utf-8')
  capture = CommandCapture(
    name=name,
    command=tuple(command),
    returncode=result.returncode,
    stdout_path=str(stdout_path),
    stderr_path=str(stderr_path),
  )
  if check and result.returncode != 0:
    if result.stdout:
      print(result.stdout)
    if result.stderr:
      print(result.stderr, file=sys.stderr)
    raise SystemExit(
      'Command failed for {name} with exit code {code}.'.format(
        name=name,
        code=result.returncode,
      )
    )
  return result, capture


def _run_cli_help(raw_root: Path) -> Tuple[str, CommandCapture]:
  result, capture = _run_command(
    'cli_help',
    (sys.executable, '-m', 'calamum_vulcan.app', '--help'),
    raw_root,
  )
  return result.stdout, capture


def _run_integration_bundle(
  suite_name: str,
  raw_root: Path,
) -> Tuple[Dict[str, Any], str, Tuple[CommandCapture, CommandCapture]]:
  base_name = suite_name.replace('-', '_')
  json_path = raw_root / '{base}.json'.format(base=base_name)
  markdown_path = raw_root / '{base}.md'.format(base=base_name)
  _, json_capture = _run_command(
    '{base}_json'.format(base=base_name),
    (
      sys.executable,
      '-m',
      'calamum_vulcan.app',
      '--integration-suite',
      suite_name,
      '--suite-format',
      'json',
      '--suite-output',
      str(json_path),
    ),
    raw_root,
  )
  _, markdown_capture = _run_command(
    '{base}_markdown'.format(base=base_name),
    (
      sys.executable,
      '-m',
      'calamum_vulcan.app',
      '--integration-suite',
      suite_name,
      '--suite-format',
      'markdown',
      '--suite-output',
      str(markdown_path),
    ),
    raw_root,
  )
  return _read_json(json_path), _read_text(markdown_path), (json_capture, markdown_capture)


def _run_execute_probe(
  name: str,
  scenario: str,
  raw_root: Path,
  export_evidence: bool,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], Tuple[CommandCapture, ...]]:
  command = [
    sys.executable,
    '-m',
    'calamum_vulcan.app',
    '--execute-flash-plan',
    '--transport-source',
    'heimdall-adapter',
    '--scenario',
    scenario,
    '--control-format',
    'json',
  ]
  evidence_payload = None
  captures = []
  if export_evidence:
    evidence_path = raw_root / '{name}_evidence.json'.format(name=name)
    command.extend(
      [
        '--export-evidence',
        '--evidence-format',
        'json',
        '--evidence-output',
        str(evidence_path),
      ]
    )
  result, capture = _run_command(name, tuple(command), raw_root)
  captures.append(capture)
  control_payload = _parse_leading_json(result.stdout)
  if export_evidence:
    evidence_payload = _read_json(raw_root / '{name}_evidence.json'.format(name=name))
  return control_payload, evidence_payload, tuple(captures)


def _copy_if_exists(source: Path, target: Path) -> bool:
  if not source.exists():
    return False
  shutil.copy2(source, target)
  return True


def _collect_readiness(
  raw_root: Path,
  refresh: bool,
) -> Tuple[str, Optional[Dict[str, Any]], Tuple[CommandCapture, ...]]:
  captures = []
  if refresh:
    _, capture = _run_command(
      'refresh_readiness_stack',
      (sys.executable, 'scripts/run_v050_readiness_stack.py'),
      raw_root,
      check=False,
    )
    captures.append(capture)
  summary = None
  if READINESS_SUMMARY_PATH.exists():
    summary = _read_json(READINESS_SUMMARY_PATH)
    _copy_if_exists(READINESS_SUMMARY_PATH, raw_root / 'readiness_summary.json')
    _copy_if_exists(READINESS_SUMMARY_MARKDOWN_PATH, raw_root / 'readiness_summary.md')
  readiness_status = 'missing'
  if summary is not None:
    readiness_status = str(summary.get('overall_status', 'unknown'))
  elif captures:
    readiness_status = 'failed' if captures[-1].returncode != 0 else 'missing'
  return readiness_status, summary, tuple(captures)


def _view_model_probe(name: str, pit_required_for_safe_path: bool) -> Dict[str, Any]:
  session = build_demo_session(name)
  package_assessment = build_demo_package_assessment(name, session=session)
  pit_inspection = build_demo_pit_inspection(
    name,
    session=session,
    package_assessment=package_assessment,
  )
  authority = build_session_authority_snapshot(
    session,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  model = build_shell_view_model(
    session,
    scenario_name=name,
    package_assessment=package_assessment,
    pit_inspection=pit_inspection,
    pit_required_for_safe_path=pit_required_for_safe_path,
  )
  return {
    'scenario': name,
    'phase_label': model.phase_label,
    'gate_label': model.gate_label,
    'launch_path': authority.selected_launch_path.value,
    'ownership': authority.ownership.value,
    'readiness': authority.readiness.value,
    'block_reason': authority.block_reason,
    'action_states': {
      action.label: action.state.value
      for action in model.control_actions
      if action.visible
    },
  }


def _scenario_map(bundle_payload: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
  return {
    str(scenario['scenario_id']): scenario
    for scenario in bundle_payload['scenarios']
  }


def _build_criteria(context: Mapping[str, Any]) -> Tuple[CriterionResult, ...]:
  pyproject = context['pyproject']
  readme_text = context['readme_text']
  changelog_text = context['changelog_text']
  cli_help = context['cli_help']
  bundles = context['bundles']
  bundle_markdown = context['bundle_markdown']
  execute_ready = context['execute_ready_control']
  execute_ready_evidence = context['execute_ready_evidence']
  execute_blocked = context['execute_blocked_control']
  qt_shell_text = context['qt_shell_text']
  normalizer_text = context['normalizer_text']
  workflow_text = context['workflow_text']
  readiness_summary = context['readiness_summary']
  readiness_plan_text = context['sprint4_readiness_plan_text']
  checklist_text = context['sprint4_checklist_text']
  ready_probe = context['ready_view_model_probe']
  blocked_probe = context['blocked_view_model_probe']
  detect_fixture_names = context['detect_fixture_names']

  sprint_close = bundles['sprint-close']
  orchestration_close = bundles['orchestration-close']
  read_side_close = bundles['read-side-close']
  safe_path_close = bundles['safe-path-close']
  orchestration_scenarios = _scenario_map(orchestration_close)
  read_side_scenarios = _scenario_map(read_side_close)
  safe_path_scenarios = _scenario_map(safe_path_close)

  runtime_scenarios = [
    scenario
    for scenario in orchestration_close['scenarios']
    if scenario['transport_source'] == 'heimdall-adapter'
  ]
  package_boundary_aligned = (
    str(pyproject['project']['version']) == '0.5.0'
    and 'local package-only Sprint 5 boundary' in readme_text
    and '## 0.5.0 - 2026-04-22' in changelog_text
  )
  publication_deferral_explicit = (
    'Do **not** publish `0.5.0` to PyPI' in checklist_text
    and 'immediate post-`0.6.0` `1.0.0` promotion gate' in readme_text
    and 'TestPyPI/PyPI rehearsal' in readiness_plan_text
  )
  readiness_green = (
    readiness_summary is not None
    and readiness_summary.get('overall_status') == 'passed'
  )
  s4_08_status = 'implemented'
  if not package_boundary_aligned:
    s4_08_status = 'partial'
  if not readiness_green:
    s4_08_status = 'open'

  criteria = [
    CriterionResult(
      sprint='0.1.0',
      criterion_id='S1-01',
      title='GUI-first shell, preflight surfaces, and sprint-close proof are present',
      status='implemented',
      priority='medium',
      impact='The original GUI-first product-shell boundary is still intact and publicly callable.',
      evidence=(
        'pyproject entry points include `calamum-vulcan` and `calamum-vulcan-gui`.',
        'CLI help still exposes `--export-evidence`, `--integration-suite`, and package-aware review flags.',
        'The generated `sprint-close` bundle still reports suite `{suite}` with {count} scenarios.'.format(
          suite=sprint_close['suite_name'],
          count=len(sprint_close['scenarios']),
        ),
      ),
      notes=(
        'This confirms the `0.1.0` shell boundary survived later extraction work.',
      ),
    ),
    CriterionResult(
      sprint='0.2.0',
      criterion_id='S2-01',
      title='Archive-backed package intake, analyzed snapshot, device registry, and reviewed flash-plan ownership remain live',
      status='implemented',
      priority='medium',
      impact='Sprint 2 ownership surfaces are still structurally embedded rather than lingering as release-only history.',
      evidence=(
        'CLI help still exposes `--package-archive`, which is the public surface for archive-backed review intake.',
        'The installed/source validation stack in `scripts/validate_installed_artifact.py` still asserts archive checksum verification, snapshot verification, and reviewed flash-plan fields.',
        'The `orchestration-close` bundle remains available as a deterministic Sprint 2 closeout surface.',
      ),
    ),
    CriterionResult(
      sprint='0.2.0',
      criterion_id='S2-02',
      title='Bounded runtime orchestration and transcript evidence remain implemented',
      status='implemented',
      priority='medium',
      impact='The first platform-governed runtime lane is still preserved with transcript retention and recovery-oriented evidence.',
      evidence=(
        'The `orchestration-close` bundle still yields runtime scenarios with Heimdall transport ownership.',
        'Runtime scenarios preserve transcript references: {value}.'.format(
          value=all(scenario['transcript_preserved'] for scenario in runtime_scenarios),
        ),
        'Bundle markdown still renders the Sprint 2 closeout narrative for `orchestration-close`.',
      ),
    ),
    CriterionResult(
      sprint='0.2.0',
      criterion_id='S2-03',
      title='The historical 0.2.0 public boundary remains evidenced',
      status='implemented',
      priority='low',
      impact='Sprint 2 release closure is still visible and has not been overwritten by later local work.',
      evidence=(
        'CHANGELOG still includes a published `0.2.0` section.',
        'README current-status guidance still treats `0.3.0` as the latest public boundary, which implies `0.2.0` was superseded rather than lost.',
      ),
    ),
    CriterionResult(
      sprint='0.3.0',
      criterion_id='S3-01',
      title='Read-side live detection, PIT inspection, and inspect-only workflow remain implemented',
      status='implemented',
      priority='medium',
      impact='Sprint 3 read-side autonomy still exists as a repo-owned review lane.',
      evidence=(
        'The `read-side-close` bundle still exposes `inspect-only-ready-review`, `native-adb-package-review`, and PIT-aware scenario evidence.',
        'The ready inspect-only scenario preserves inspection posture `{posture}` with transport state `{state}`.'.format(
          posture=read_side_scenarios['inspect-only-ready-review']['inspection_posture'],
          state=read_side_scenarios['inspect-only-ready-review']['transport_state'],
        ),
        'Bundle markdown still carries the Sprint 3 `read-side-close` heading.',
      ),
    ),
    CriterionResult(
      sprint='0.3.0',
      criterion_id='S3-02',
      title='Fallback visibility and delegated-path honesty remain implemented',
      status='implemented',
      priority='medium',
      impact='Fastboot and exhausted-fallback surfaces still read as explicit review boundaries rather than silent native ownership.',
      evidence=(
        'The `fastboot-fallback-review` scenario still reports live source `{source}` and fallback posture `{posture}`.'.format(
          source=read_side_scenarios['fastboot-fallback-review']['live_source'],
          posture=read_side_scenarios['fastboot-fallback-review']['live_fallback_posture'],
        ),
        'The `fallback-exhausted-review` scenario still preserves inspection posture `{posture}`.'.format(
          posture=read_side_scenarios['fallback-exhausted-review']['inspection_posture'],
        ),
      ),
    ),
    CriterionResult(
      sprint='0.3.0',
      criterion_id='S3-03',
      title='The read-side-close evidence surface and public 0.3.0 boundary remain intact',
      status='implemented',
      priority='medium',
      impact='Sprint 3 shipped surfaces are still coherent across code and release metadata.',
      evidence=(
        'README still states `0.3.0` is the current public Calamum Vulcan release.',
        'CHANGELOG still contains the `0.3.0` release section.',
        'The `read-side-close` bundle still exists and renders via both JSON and Markdown outputs.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-01',
      title='Session-authority and safe-path vocabulary are implemented and consumed',
      status='implemented',
      priority='high',
      impact='The core Sprint 5 extraction seam is live rather than prose-only.',
      evidence=(
        'Ready probe reports launch path `{launch}` with ownership `{owner}` and readiness `{ready}`.'.format(
          launch=ready_probe['launch_path'],
          owner=ready_probe['ownership'],
          ready=ready_probe['readiness'],
        ),
        'Blocked probe reports launch path `{launch}` with block reason `{reason}`.'.format(
          launch=blocked_probe['launch_path'],
          reason=blocked_probe['block_reason'],
        ),
        'The `safe-path-close` bundle is now generated locally, which means the formerly planned suite name is fully instantiated.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-02',
      title='Device, package, and PIT alignment hardening is implemented',
      status='implemented',
      priority='high',
      impact='Safe-path readiness now narrows or blocks on missing or mismatched PIT/alignment truth instead of remaining descriptive only.',
      evidence=(
        'The `read-pit-required-review` scenario remains blocked with gate label `{gate}`.'.format(
          gate=safe_path_scenarios['read-pit-required-review']['gate_label'],
        ),
        'The `pit-mismatch-block-review` scenario still preserves PIT/package alignment `{alignment}`.'.format(
          alignment=safe_path_scenarios['pit-mismatch-block-review']['pit_package_alignment'],
        ),
        'Blocked authority probe keeps launch path `{launch}` rather than implying a ready safe-path claim.'.format(
          launch=blocked_probe['launch_path'],
        ),
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-03',
      title='The bounded safe-path execute lane is implemented in the platform-owned CLI path',
      status='implemented',
      priority='high',
      impact='Sprint 5 now owns one real, narrow execution lane instead of keeping safe-path strictly aspirational.',
      evidence=(
        'Ready execute control reports `execution_allowed={value}`.'.format(
          value=execute_ready['execution_allowed'],
        ),
        'Blocked execute control reports `execution_allowed={value}` with transport state `{state}`.'.format(
          value=execute_blocked['execution_allowed'],
          state=execute_blocked['transport']['state'],
        ),
        'Ready execute evidence preserves transport state `{state}` plus authority ownership `{owner}`.'.format(
          state=execute_ready_evidence['transport']['state'],
          owner=execute_ready_evidence['authority']['ownership'],
        ),
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-04',
      title='Runtime hygiene and Heimdall detect taxonomy are implemented with explicit failure classes',
      status='implemented',
      priority='high',
      impact='The runtime lane now distinguishes missing-device, runtime-failure, and unparsed-output cases instead of flattening them into one opaque Samsung miss.',
      evidence=(
        'The Heimdall normalizer source now carries `no_device`, `runtime_failure`, and `unparsed_output` classifications.',
        'The Qt shell now contains `_archive_heimdall_detect_diagnostic`, `_apply_unified_heimdall_detection_trace`, and the real `_run_read_pit_workflow` path.',
        'Stored detect fixtures now cover multiple Samsung outcomes: {fixtures}.'.format(
          fixtures=', '.join(detect_fixture_names) if detect_fixture_names else 'none',
        ),
      ),
      notes=(
        'Real-hardware transcript growth can continue as carry-forward debt, but Sprint 5 no longer depends on a single canned detect transcript.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-05',
      title='The GUI workflow now reflects the settled Sprint 5 control flow',
      status='implemented',
      priority='high',
      impact='The operator shell now owns the truthful Sprint 5 deck progression instead of teaching one workflow while leaving the real path hidden in CLI-only surfaces.',
      evidence=(
        'The Qt shell guidance now states `Detect device -> Read PIT -> Load package -> Execute flash plan -> Export evidence`.',
        'The shell now contains `_load_package_archive`, `_run_execute_flash_plan_workflow`, and `_continue_after_recovery` in addition to the dedicated `Read PIT` workflow.',
        'The `safe-path-close` bundle preserves `Execute flash plan=next` for the ready review and `Export evidence=next` for runtime closeout, which matches the current deck contract.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-06',
      title='Safe-path closeout evidence and the Sprint 5 readiness orchestrator are implemented',
      status='implemented',
      priority='high',
      impact='Sprint 5 now has real integrated closeout proof and a repeatable multi-lane readiness sweep.',
      evidence=(
        'The `safe-path-close` bundle now exists with {count} scenarios.'.format(
          count=len(safe_path_close['scenarios']),
        ),
        'Bundle markdown heading is `{heading}`.'.format(
          heading=bundle_markdown['safe-path-close'].splitlines()[0],
        ),
        'Readiness status is `{status}`.'.format(
          status='missing' if readiness_summary is None else readiness_summary['overall_status'],
        ),
      ),
      notes=(
        'If the readiness summary is green, Sprint 5 broad validation is no longer hypothetical.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-07',
      title='Package-only closeout discipline and publication deferral are implemented',
      status='implemented' if publication_deferral_explicit else 'partial',
      priority='high',
      impact='Sprint 5 now closes as a local package boundary while preserving public publication as a later promotion gate instead of pretending unfinished release work is part of the sprint definition.',
      evidence=(
        'The closeout checklist explicitly says `Do **not** publish `0.5.0` to PyPI`.',
        'README now distinguishes the local `0.5.0` package-only boundary from the public `0.3.0` release.',
        'The readiness plan now treats TestPyPI/PyPI rehearsal as deferred carry-forward work rather than Sprint 5 acceptance criteria.',
      ),
      next_actions=(
        'Keep the publication workflow dormant until the immediate post-`0.6.0` `1.0.0` promotion gate if any doc surface still implies Sprint 5 depends on public upload.',
      ) if not publication_deferral_explicit else (),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S4-08',
      title='The local 0.5.0 package boundary metadata and readiness proof are aligned',
      status=s4_08_status,
      priority='critical',
      impact='Sprint 5 closeout is only honest when the repository version, release surfaces, and broad validation evidence all agree on the local package boundary being sealed.',
      evidence=(
        'pyproject now reports version `{version}`.'.format(
          version=pyproject['project']['version'],
        ),
        'README now frames `0.5.0` as the local package-only boundary while keeping `0.3.0` as the public release.',
        'CHANGELOG now includes the local `0.5.0` boundary section.',
        'Readiness summary status: `{status}`.'.format(
          status='missing' if readiness_summary is None else readiness_summary.get('overall_status', 'unknown'),
        ),
      ),
      next_actions=(
        'Re-run the full Sprint 5 readiness stack until all selected lanes are green.',
      ) if not readiness_green else (
        'Finish aligning any remaining tracked release surface to the local `0.5.0` boundary if metadata still diverges.',
      ) if not package_boundary_aligned else (),
    ),
  ]

  return tuple(criteria)


def _build_opportunistic_finds(context: Mapping[str, Any]) -> Tuple[Finding, ...]:
  return (
    Finding(
      finding_id='X-01',
      title='Safe-path closeout proof is already wired into multiple downstream validators',
      severity='medium',
      category='extra',
      summary='Sprint 5 closeout proof is broader than the stale planning shells imply.',
      evidence=(
        '`scripts/validate_installed_artifact.py` now verifies the installed `safe-path-close` bundle and execute lane.',
        '`scripts/run_scripted_simulation_suite.py` already carries safe-path execute and `safe-path-close` parity proof.',
        '`scripts/run_testpypi_rehearsal.py` already checks the installed `safe-path-close` bundle during registry rehearsal.',
      ),
    ),
    Finding(
      finding_id='X-02',
      title='The GUI already has a real Read PIT workflow with bounded fallback',
      severity='medium',
      category='extra',
      summary='The control-deck narrowing work is ahead of the old “planned only” narrative for the Sprint 5 operator lane.',
      evidence=(
        '`qt_shell.py` includes `_run_read_pit_workflow`, `_apply_read_pit_print_trace`, `_apply_read_pit_download_trace`, and `_finish_read_pit_workflow`.',
      ),
    ),
    Finding(
      finding_id='X-03',
      title='Heimdall detect normalization is materially stronger than the stale docs claim',
      severity='medium',
      category='extra',
      summary='The lower transport path now distinguishes multiple failure classes instead of collapsing them into one opaque miss.',
      evidence=(
        '`normalizer.py` classifies detect failures as `no_device`, `runtime_failure`, and `unparsed_output`.',
        '`qt_shell.py` archives detect diagnostics when Heimdall cannot produce a trustworthy identity.',
      ),
    ),
    Finding(
      finding_id='X-04',
      title='Windows runtime ergonomics were hardened as opportunistic Sprint 5 gains',
      severity='low',
      category='extra',
      summary='The transport/runtime lane already includes host-specific hardening beyond the minimum closeout claim.',
      evidence=(
        '`adapters/heimdall/runtime.py` now resolves common Windows Heimdall locations in addition to PATH.',
        '`launch_shell(...)` maximizes normal interactive runs while keeping duration-bounded/offscreen validation deterministic.',
      ),
    ),
  )


def _build_deviations(context: Mapping[str, Any]) -> Tuple[Finding, ...]:
  sprint4_evidence_text = context['sprint4_evidence_text']
  readiness_plan_text = context['sprint4_readiness_plan_text']
  deviations = []
  if any(
    needle in sprint4_evidence_text
    for needle in (
      '| `FS5-06` | planned |',
      '| `FS5-07` | planned |',
      '| `FS5-08` | planned |',
    )
  ):
    deviations.append(
      Finding(
        finding_id='D-01',
        title='Sprint 5 evidence ledger still understates implemented work',
        severity='high',
        category='doc-drift',
        summary='The local execution-evidence register still understates the current Sprint 5 closeout state.',
        evidence=(
          'The evidence ledger still contains one or more planned rows for `FS5-06`, `FS5-07`, or `FS5-08`.',
          'The workspace now generates `safe-path-close`, runs `run_v050_readiness_stack.py`, and exposes the bounded execute lane.',
        ),
      )
    )
  if 'safe-path-close` bundle does not exist yet' in readiness_plan_text:
    deviations.append(
      Finding(
        finding_id='D-02',
        title='The Sprint 5 readiness plan still says safe-path-close does not exist yet',
        severity='high',
        category='doc-drift',
        summary='The readiness plan is still behind implementation reality and will mislead any audit that reads docs without probing code.',
        evidence=(
          '`Samsung_Android_Flashing_Platform_0.5.0_Testing_and_Readiness_Plan.md` still says `the deterministic `safe-path-close` bundle does not exist yet`.',
          'The current audit generated `safe-path-close` JSON and Markdown outputs directly from the live CLI.',
        ),
      )
    )
  return tuple(deviations)


def _build_sprint_counts(criteria: Sequence[CriterionResult]) -> Dict[str, Dict[str, int]]:
  counts = {
    sprint: {'implemented': 0, 'partial': 0, 'open': 0}
    for sprint in SPRINT_LABELS
  }
  for criterion in criteria:
    counts.setdefault(criterion.sprint, {'implemented': 0, 'partial': 0, 'open': 0})
    counts[criterion.sprint][criterion.status] += 1
  return counts


def _render_markdown(summary: AuditSummary) -> str:
  lines = [
    '# Calamum Vulcan `0.5.0` execution-timeline audit',
    '',
    '- captured at: `{captured}`'.format(captured=summary.captured_at_utc),
    '- repo root: `{root}`'.format(root=summary.repo_root),
    '- output root: `{root}`'.format(root=summary.output_root),
    '- current repository package version: `{version}`'.format(version=summary.current_package_version),
    '- target sprint: `{target}` — {label}'.format(
      target=summary.target_sprint,
      label=SPRINT_LABELS[summary.target_sprint],
    ),
    '- readiness status: `{status}`'.format(status=summary.readiness_status),
    '',
    '## Executive summary',
    '',
    '- audited criteria: `{count}`'.format(count=len(summary.criteria)),
    '- implemented: `{count}`'.format(count=summary.status_counts.get('implemented', 0)),
    '- partial: `{count}`'.format(count=summary.status_counts.get('partial', 0)),
    '- open: `{count}`'.format(count=summary.status_counts.get('open', 0)),
    '- opportunistic implemented finds: `{count}`'.format(count=len(summary.opportunistic_finds)),
    '- notable deviations: `{count}`'.format(count=len(summary.deviations)),
    '',
    '## Aggregate status by sprint',
    '',
    '| Sprint | Planned focus | Implemented | Partial | Open |',
    '| --- | --- | ---: | ---: | ---: |',
  ]
  for sprint in SPRINT_LABELS:
    sprint_counts = summary.sprint_counts.get(sprint, {})
    lines.append(
      '| `{sprint}` | {label} | {implemented} | {partial} | {open_items} |'.format(
        sprint=sprint,
        label=SPRINT_LABELS[sprint],
        implemented=sprint_counts.get('implemented', 0),
        partial=sprint_counts.get('partial', 0),
        open_items=sprint_counts.get('open', 0),
      )
    )

  open_or_partial = sorted(
    [criterion for criterion in summary.criteria if criterion.status != 'implemented'],
    key=lambda criterion: (_status_key(criterion.status), criterion.criterion_id),
  )
  lines.extend(
    [
      '',
      '## Highest-priority remaining items',
      '',
    ]
  )
  if not open_or_partial:
    lines.extend(['- No open or partial criteria remain.', ''])
  else:
    for criterion in open_or_partial:
      lines.extend(
        [
          '### `{id}` — {title}'.format(
            id=criterion.criterion_id,
            title=criterion.title,
          ),
          '',
          '- sprint: `{sprint}`'.format(sprint=criterion.sprint),
          '- status: `{status}`'.format(status=criterion.status),
          '- priority: `{priority}`'.format(priority=criterion.priority),
          '- impact: {impact}'.format(impact=criterion.impact),
          '- evidence:',
        ]
      )
      for item in criterion.evidence:
        lines.append('  - {item}'.format(item=item))
      if criterion.next_actions:
        lines.append('- next actions:')
        for item in criterion.next_actions:
          lines.append('  - {item}'.format(item=item))
      if criterion.notes:
        lines.append('- notes:')
        for item in criterion.notes:
          lines.append('  - {item}'.format(item=item))
      lines.append('')

  lines.extend(
    [
      '## Opportunistic implemented finds',
      '',
    ]
  )
  for finding in summary.opportunistic_finds:
    lines.extend(
      [
        '### `{id}` — {title}'.format(
          id=finding.finding_id,
          title=finding.title,
        ),
        '',
        '- severity: `{severity}`'.format(severity=finding.severity),
        '- summary: {summary}'.format(summary=finding.summary),
        '- evidence:',
      ]
    )
    for item in finding.evidence:
      lines.append('  - {item}'.format(item=item))
    lines.append('')

  lines.extend(
    [
      '## Notable deviations',
      '',
    ]
  )
  for finding in summary.deviations:
    lines.extend(
      [
        '### `{id}` — {title}'.format(
          id=finding.finding_id,
          title=finding.title,
        ),
        '',
        '- severity: `{severity}`'.format(severity=finding.severity),
        '- category: `{category}`'.format(category=finding.category),
        '- summary: {summary}'.format(summary=finding.summary),
        '- evidence:',
      ]
    )
    for item in finding.evidence:
      lines.append('  - {item}'.format(item=item))
    lines.append('')

  lines.extend(
    [
      '## Detailed criterion ledger',
      '',
      '| ID | Sprint | Status | Title |',
      '| --- | --- | --- | --- |',
    ]
  )
  for criterion in summary.criteria:
    lines.append(
      '| `{id}` | `{sprint}` | `{status}` | {title} |'.format(
        id=criterion.criterion_id,
        sprint=criterion.sprint,
        status=criterion.status,
        title=criterion.title,
      )
    )

  lines.extend(
    [
      '',
      '## Raw probe anchors',
      '',
      '| Capture | Return code | Stdout | Stderr |',
      '| --- | ---: | --- | --- |',
    ]
  )
  for capture in summary.command_captures:
    lines.append(
      '| `{name}` | `{code}` | `{stdout}` | `{stderr}` |'.format(
        name=capture.name,
        code=capture.returncode,
        stdout=capture.stdout_path,
        stderr=capture.stderr_path,
      )
    )

  lines.extend(
    [
      '',
      '## Interpretation guardrails',
      '',
      '- `implemented` means the planned surface is materially present in the current workspace and was probed through code, CLI, or closeout artifacts during this audit.',
      '- `partial` means meaningful Sprint work exists, but a material portion of the planned surface is still stubbed, thinly evidenced, or lagging the settled operator contract.',
      '- `open` means the planned end-state remains unclosed for the current `0.5.0` target.',
      '- documentation drift is reported separately so release-boundary lag does not get misread as code-level non-implementation.',
      '',
    ]
  )
  return '\n'.join(lines)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description='Audit the current Calamum Vulcan implementation against the 0.1.0-0.5.0 sprint timeline.',
  )
  parser.add_argument(
    '--output-root',
    default=str(DEFAULT_OUTPUT_ROOT),
    help='Directory where the audit report and raw probe outputs should be written.',
  )
  parser.add_argument(
    '--refresh-readiness',
    action='store_true',
    help='Re-run the Sprint 5 readiness stack before scoring the audit.',
  )
  parser.add_argument(
    '--captured-at-utc',
    default='2026-04-22T00:00:00Z',
    help='Timestamp string recorded in the top-level audit report.',
  )
  return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = _parse_args(argv)
  output_root = Path(args.output_root).resolve()
  raw_root = output_root / RAW_DIR_NAME
  _ensure_clean_dir(output_root)
  raw_root.mkdir(parents=True, exist_ok=True)
  progress_path = output_root / 'progress.log'
  _append_progress(progress_path, 'initialized_output_root')

  pyproject = tomllib.loads(_read_text(PYPROJECT_PATH))
  readme_text = _read_text(README_PATH)
  changelog_text = _read_text(CHANGELOG_PATH)
  workflow_text = _read_text(WORKFLOW_PATH)
  sprint4_evidence_text = _read_text(SPRINT4_EVIDENCE_PATH)
  sprint4_readiness_plan_text = _read_text(SPRINT4_READINESS_PLAN_PATH)
  sprint4_checklist_text = _read_text(SPRINT4_CHECKLIST_PATH)
  qt_shell_text = _read_text(REPO_ROOT / 'calamum_vulcan' / 'app' / 'qt_shell.py')
  normalizer_text = _read_text(REPO_ROOT / 'calamum_vulcan' / 'adapters' / 'heimdall' / 'normalizer.py')
  _append_progress(progress_path, 'loaded_static_text_surfaces')

  command_captures = []
  cli_help, capture = _run_cli_help(raw_root)
  command_captures.append(capture)
  _append_progress(progress_path, 'captured_cli_help')

  bundles = {}
  bundle_markdown = {}
  for suite_name in ('sprint-close', 'orchestration-close', 'read-side-close', 'safe-path-close'):
    bundle_payload, markdown_text, captures = _run_integration_bundle(suite_name, raw_root)
    bundles[suite_name] = bundle_payload
    bundle_markdown[suite_name] = markdown_text
    command_captures.extend(captures)
  _append_progress(progress_path, 'captured_integration_bundles')

  execute_ready_control, execute_ready_evidence, captures = _run_execute_probe(
    'ready_execute_control',
    'ready',
    raw_root,
    export_evidence=True,
  )
  command_captures.extend(captures)
  _append_progress(progress_path, 'captured_ready_execute_probe')

  execute_blocked_control, _, captures = _run_execute_probe(
    'blocked_execute_control',
    'blocked',
    raw_root,
    export_evidence=False,
  )
  command_captures.extend(captures)
  _append_progress(progress_path, 'captured_blocked_execute_probe')

  readiness_status, readiness_summary, captures = _collect_readiness(
    raw_root,
    refresh=args.refresh_readiness,
  )
  command_captures.extend(captures)
  _append_progress(progress_path, 'collected_readiness_state')

  ready_view_model_probe = _view_model_probe('ready', pit_required_for_safe_path=True)
  _append_progress(progress_path, 'built_ready_view_model_probe')
  blocked_view_model_probe = _view_model_probe('blocked', pit_required_for_safe_path=True)
  _append_progress(progress_path, 'built_blocked_view_model_probe')
  _write_json(raw_root / 'ready_view_model_probe.json', ready_view_model_probe)
  _write_json(raw_root / 'blocked_view_model_probe.json', blocked_view_model_probe)
  _append_progress(progress_path, 'wrote_view_model_probes')

  detect_fixture_names = tuple(
    name for name in available_adapter_fixtures() if name.startswith('detect-')
  )

  raw_probe_summary = {
    'cli_flags_present': {
      flag: (flag in cli_help)
      for flag in (
        '--integration-suite',
        '--export-evidence',
        '--package-archive',
        '--execute-flash-plan',
      )
    },
    'bundle_suite_names': {
      suite_name: payload['suite_name']
      for suite_name, payload in bundles.items()
    },
    'execute_ready_control': execute_ready_control,
    'execute_blocked_control': execute_blocked_control,
    'execute_ready_evidence_summary': {
      'transport_state': execute_ready_evidence['transport']['state'],
      'authority_ownership': execute_ready_evidence['authority']['ownership'],
      'safe_path_governance_line_present': any(
        '[SAFE-PATH] governance=platform_supervised' in line
        for line in execute_ready_evidence['log_lines']
      ),
    },
    'detect_fixture_names': detect_fixture_names,
    'ready_view_model_probe': ready_view_model_probe,
    'blocked_view_model_probe': blocked_view_model_probe,
    'readiness_status': readiness_status,
  }
  _write_json(raw_root / 'probe_summary.json', raw_probe_summary)
  _append_progress(progress_path, 'wrote_probe_summary')

  context = {
    'pyproject': pyproject,
    'readme_text': readme_text,
    'changelog_text': changelog_text,
    'workflow_text': workflow_text,
    'sprint4_evidence_text': sprint4_evidence_text,
    'sprint4_readiness_plan_text': sprint4_readiness_plan_text,
    'sprint4_checklist_text': sprint4_checklist_text,
    'qt_shell_text': qt_shell_text,
    'normalizer_text': normalizer_text,
    'cli_help': cli_help,
    'bundles': bundles,
    'bundle_markdown': bundle_markdown,
    'execute_ready_control': execute_ready_control,
    'execute_ready_evidence': execute_ready_evidence,
    'execute_blocked_control': execute_blocked_control,
    'ready_view_model_probe': ready_view_model_probe,
    'blocked_view_model_probe': blocked_view_model_probe,
    'detect_fixture_names': detect_fixture_names,
    'readiness_summary': readiness_summary,
  }

  criteria = _build_criteria(context)
  opportunistic_finds = _build_opportunistic_finds(context)
  deviations = _build_deviations(context)
  status_counts = dict(Counter(criterion.status for criterion in criteria))
  sprint_counts = _build_sprint_counts(criteria)
  summary = AuditSummary(
    captured_at_utc=args.captured_at_utc,
    repo_root=str(REPO_ROOT),
    output_root=str(output_root),
    current_package_version=str(pyproject['project']['version']),
    target_sprint='0.5.0',
    criteria=criteria,
    opportunistic_finds=opportunistic_finds,
    deviations=deviations,
    command_captures=tuple(command_captures),
    readiness_status=readiness_status,
    status_counts=status_counts,
    sprint_counts=sprint_counts,
    raw_probe_summary=raw_probe_summary,
  )

  json_path = output_root / 'v050_timeline_audit.json'
  markdown_path = output_root / 'v050_timeline_audit.md'
  _write_json(json_path, asdict(summary))
  markdown_path.write_text(_render_markdown(summary) + '\n', encoding='utf-8')
  _append_progress(progress_path, 'wrote_final_reports')

  _print(
    [
      'audit_root="{root}"'.format(root=output_root),
      'report_json="{path}"'.format(path=json_path),
      'report_markdown="{path}"'.format(path=markdown_path),
      'criteria_total="{count}"'.format(count=len(criteria)),
      'implemented="{count}"'.format(count=status_counts.get('implemented', 0)),
      'partial="{count}"'.format(count=status_counts.get('partial', 0)),
      'open="{count}"'.format(count=status_counts.get('open', 0)),
      'opportunistic_finds="{count}"'.format(count=len(opportunistic_finds)),
      'deviations="{count}"'.format(count=len(deviations)),
      'readiness_status="{status}"'.format(status=readiness_status),
    ]
  )
  return 0


if __name__ == '__main__':
  raise SystemExit(main())

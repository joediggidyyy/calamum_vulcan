"""Audit current implementation against the final-frame 0.6.0 autonomy target."""

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

from calamum_vulcan.app.demo import available_transport_sources


DEFAULT_OUTPUT_ROOT = REPO_ROOT / 'temp' / 'v060_alignment_audit'
RAW_DIR_NAME = 'raw'
DOCS_ROOT = REPO_ROOT / 'docs'
PYPROJECT_PATH = REPO_ROOT / 'pyproject.toml'
README_PATH = REPO_ROOT / 'README.md'
CHANGELOG_PATH = REPO_ROOT / 'CHANGELOG.md'
PLAN_PATH = DOCS_ROOT / 'Samsung_Android_Flashing_Platform_Research_Report_and_Build_Plan.md'
SPRINT6_EXECUTION_SURFACE_PATH = DOCS_ROOT / 'Samsung_Android_Flashing_Platform_0.6.0_Execution_Surface.md'
SPRINT6_CHECKLIST_PATH = DOCS_ROOT / 'Samsung_Android_Flashing_Platform_0.6.0_Execution_Checklist.md'
APP_MAIN_PATH = REPO_ROOT / 'calamum_vulcan' / 'app' / '__main__.py'
APP_DEMO_PATH = REPO_ROOT / 'calamum_vulcan' / 'app' / 'demo.py'
APP_INTEGRATION_PATH = REPO_ROOT / 'calamum_vulcan' / 'app' / 'integration.py'
SAFE_PATH_MODEL_PATH = REPO_ROOT / 'calamum_vulcan' / 'domain' / 'safe_path' / 'model.py'
V040_AUDIT_PATH = REPO_ROOT / 'scripts' / 'run_v040_timeline_audit.py'


SPRINT_LABELS = {
  '0.1.0': 'GUI-first product shell',
  '0.2.0': 'orchestration ownership',
  '0.3.0': 'read-side autonomy',
  '0.4.0': 'session and safe-path extraction',
  '0.5.0': 'efficient integrated transport extraction',
  '0.6.0': 'fully functional Calamum-owned integrated Samsung runtime',
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
  """One notable implemented gain or deviation."""

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
  current_repository_version: str
  target_sprint: str
  criteria: Tuple[CriterionResult, ...]
  opportunistic_finds: Tuple[Finding, ...]
  deviations: Tuple[Finding, ...]
  final_frame_closeout_map: Tuple[str, ...]
  command_captures: Tuple[CommandCapture, ...]
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


def _scenario_map(bundle_payload: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
  return {
    str(scenario['scenario_id']): scenario
    for scenario in bundle_payload['scenarios']
  }


def _doc_matches(pattern: str) -> Tuple[str, ...]:
  return tuple(
    sorted(
      str(path.relative_to(REPO_ROOT))
      for path in DOCS_ROOT.rglob(pattern)
    )
  )


def _contains(text: str, needle: str) -> bool:
  return needle in text


def _build_criteria(context: Mapping[str, Any]) -> Tuple[CriterionResult, ...]:
  pyproject = context['pyproject']
  plan_text = context['plan_text']
  cli_help = context['cli_help']
  bundles = context['bundles']
  app_main_text = context['app_main_text']
  demo_text = context['demo_text']
  integration_text = context['integration_text']
  safe_path_text = context['safe_path_text']
  v040_audit_text = context['v040_audit_text']
  sprint6_execution_surface_text = context['sprint6_execution_surface_text']
  sprint6_checklist_text = context['sprint6_checklist_text']
  readme_text = context['readme_text']
  changelog_text = context['changelog_text']
  sprint5_doc_matches = context['sprint5_doc_matches']
  sprint6_doc_matches = context['sprint6_doc_matches']
  promotion_gate_doc_matches = context['promotion_gate_doc_matches']
  transport_sources = context['transport_sources']
  execute_ready_control = context['execute_ready_control']
  execute_ready_evidence = context['execute_ready_evidence']
  execute_blocked_control = context['execute_blocked_control']

  sprint_close = bundles['sprint-close']
  orchestration_close = bundles['orchestration-close']
  read_side_close = bundles['read-side-close']
  safe_path_close = bundles['safe-path-close']
  read_side_scenarios = _scenario_map(read_side_close)
  safe_path_scenarios = _scenario_map(safe_path_close)
  support_contract_markers = (
    'detect -> PIT -> package-aligned execution -> transcript/evidence -> recovery/resume',
    '`integrated-runtime`',
    'explicit fallback, oracle, migration, or historical delegated lane only',
  )
  blocker_inventory_markers = (
    'Current blocker inventory frozen by `FS6-01`',
    '`S6-02`',
    '`S6-03`',
    '`S6-04`',
  )
  support_contract_frozen = all(
    _contains(sprint6_execution_surface_text, marker)
    for marker in support_contract_markers
  )
  blocker_inventory_frozen = all(
    _contains(sprint6_checklist_text, marker)
    for marker in blocker_inventory_markers
  )
  integrated_runtime_token_present = 'integrated-runtime' in transport_sources
  s6_01_status = 'open'
  if support_contract_frozen or blocker_inventory_frozen or integrated_runtime_token_present:
    s6_01_status = 'partial'
  if support_contract_frozen and blocker_inventory_frozen and integrated_runtime_token_present:
    s6_01_status = 'implemented'

  safe_path_ready_live_source = safe_path_scenarios['safe-path-ready-review']['live_source']
  shared_cli_native_usb_closed = (
    'VulcanUSBScanner' in app_main_text
    and 'build_usb_live_detection_session' in app_main_text
    and 'build_detect_device_command_plan' not in app_main_text
    and 'build_heimdall_live_detection_session' not in app_main_text
  )
  s6_02_status = 'partial'
  if safe_path_ready_live_source == 'usb' and shared_cli_native_usb_closed:
    s6_02_status = 'implemented'

  criteria = [
    CriterionResult(
      sprint='0.1.0',
      criterion_id='S1-01',
      title='GUI-first product shell remains materially implemented',
      status='implemented',
      priority='medium',
      impact='The final-frame stack can build on an already-real shell instead of redoing the product surface from scratch.',
      evidence=(
        'CLI help still exposes `--integration-suite`, `--export-evidence`, and GUI-launch review surfaces.',
        'The generated `sprint-close` bundle still reports suite `{suite}` across {count} integrated scenarios.'.format(
          suite=sprint_close['suite_name'],
          count=len(sprint_close['scenarios']),
        ),
        'Current public metadata still identifies the project as a GUI-first Samsung flashing platform rather than a raw backend wrapper.',
      ),
    ),
    CriterionResult(
      sprint='0.2.0',
      criterion_id='S2-01',
      title='Platform-owned orchestration, package review, and evidence surfaces remain implemented',
      status='implemented',
      priority='medium',
      impact='The final transport replacement can inherit existing plan/evidence/reporting contracts instead of inventing them late.',
      evidence=(
        'The `orchestration-close` bundle still renders and preserves runtime evidence for adapter-backed scenarios.',
        'CLI help still exposes `--package-archive`, proving package-intake review remains a first-class public surface.',
        'Installed-artifact validation still exercises archive-backed review, flash-plan evidence, and transcript-aware runtime proof.',
      ),
    ),
    CriterionResult(
      sprint='0.3.0',
      criterion_id='S3-01',
      title='Repo-owned read-side detection and PIT-aware inspection remain implemented',
      status='implemented',
      priority='medium',
      impact='The final frame does not need to recreate read-side state ownership; it needs to finish the Samsung download-mode and write-side transport handoff.',
      evidence=(
        'The `read-side-close` bundle still exists with suite `{suite}`.'.format(
          suite=read_side_close['suite_name'],
        ),
        'The `native-adb-package-review` scenario still reports live source `{source}` with PIT alignment `{alignment}`.'.format(
          source=read_side_scenarios['native-adb-package-review']['live_source'],
          alignment=read_side_scenarios['native-adb-package-review']['pit_package_alignment'],
        ),
        'The `fastboot-fallback-review` scenario still keeps fallback source `{source}` explicit.'.format(
          source=read_side_scenarios['fastboot-fallback-review']['live_source'],
        ),
      ),
    ),
    CriterionResult(
      sprint='0.4.0',
      criterion_id='S4-01',
      title='Safe-path governance and bounded execute evidence remain implemented',
      status='implemented',
      priority='high',
      impact='The final-frame stack can preserve the current governance/evidence shell while swapping out the delegated lower transport beneath it.',
      evidence=(
        'The `safe-path-close` bundle still exists with {count} integrated scenarios.'.format(
          count=len(safe_path_close['scenarios']),
        ),
        'Ready execute evidence preserves authority ownership `{owner}` and transport state `{state}`.'.format(
          owner=execute_ready_evidence['authority']['ownership'],
          state=execute_ready_evidence['transport']['state'],
        ),
        'Safe-path contract text still states `Do not claim default native transport in Sprint 0.4.0.`, which keeps the lower boundary honest.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S5-01',
      title='Sprint 5 is now correctly scoped as efficient integrated transport extraction',
      status='implemented',
      priority='high',
      impact='The roadmap no longer forces Sprint 5 to pretend it is already the first fully restored public flashing boundary.',
      evidence=(
        'The master plan now defines Sprint 5 as `efficient integrated transport extraction` rather than `default native transport on supported matrix`.',
        'Dedicated Sprint 5 authority surfaces now exist: {matches}.'.format(
          matches=', '.join(sprint5_doc_matches),
        ),
        'The Sprint 5 shell explicitly says the boundary is package-only and not yet the first fully restored polished flashing boundary.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S5-02',
      title='Integrated Samsung extraction is still materially incomplete at Sprint 5 scope',
      status='open',
      priority='critical',
      impact='Even under the updated roadmap, Sprint 5 cannot close honestly if the critical native Samsung seams are still missing.',
      evidence=(
        'Available transport sources remain `{sources}`.'.format(
          sources='`, `'.join(transport_sources),
        ),
        'The `safe-path-runtime-complete` scenario still runs with transport source `{source}`.'.format(
          source=safe_path_scenarios['safe-path-runtime-complete']['transport_source'],
        ),
        'CLI execution still says `Bounded safe-path execution currently requires --transport-source heimdall-adapter so the delegated lower transport remains explicit.`',
      ),
      next_actions=(
        'Land Calamum-owned supported-path seams for Samsung download-mode detect, PIT acquisition, and write execution.',
        'Keep external Heimdall visible only as bounded fallback, migration aid, or regression oracle while Sprint 5 extraction closes, and allow embedded Heimdall-derived transport reuse where it preserves functionality without remaining an operator-visible dependency.',
      ),
    ),
    CriterionResult(
      sprint='0.5.0',
      criterion_id='S5-03',
      title='Sprint 5 / Sprint 6 / `1.0.0` authority surfaces now exist',
      status='implemented',
      priority='high',
      impact='The final-frame work now has explicit authority shells for extraction, autonomy closeout, and post-autonomy promotion instead of relying on the master plan alone.',
      evidence=(
        'Sprint 5 docs: {matches}.'.format(
          matches=', '.join(sprint5_doc_matches),
        ),
        'Sprint 6 docs: {matches}.'.format(
          matches=', '.join(sprint6_doc_matches),
        ),
        '`1.0.0` promotion-gate docs: {matches}.'.format(
          matches=', '.join(promotion_gate_doc_matches),
        ),
      ),
    ),
    CriterionResult(
      sprint='0.6.0',
      criterion_id='S6-01',
      title='Sprint 6 support contract and blocker inventory are now explicitly frozen',
      status=s6_01_status,
      priority='critical',
      impact='The final autonomy push now has one explicit meaning for the supported runtime and one bounded blocker list, which prevents Sprint 6 execution from drifting into another discovery loop.',
      evidence=(
        'The Sprint 6 execution surface now freezes the supported path as `detect -> PIT -> package-aligned execution -> transcript/evidence -> recovery/resume` with no required external Heimdall installation or standalone Heimdall CLI.',
        'Transport-source contract tokens now read `{sources}`, with `integrated-runtime` reserved as the canonical supported-path token while `heimdall-adapter` remains the explicit historical delegated lane.'.format(
          sources='`, `'.join(transport_sources),
        ),
        'The Sprint 6 checklist now records a current blocker inventory for `S6-02` through `S6-04` rather than leaving the opening stack as unbounded discovery.',
      ),
      notes=(
        'FS6-01 freezes the contract and blocker map; it does not by itself claim that the integrated runtime is already implemented.',
      ),
    ),
    CriterionResult(
      sprint='0.6.0',
      criterion_id='S6-02',
      title='Supported-path Samsung detection and identity now close natively in shared runtime surfaces',
      status=s6_02_status,
      priority='high',
      impact='Sprint 6 can now start the supported Samsung lane through native repo-owned download-mode identity instead of defaulting to an external Heimdall detect seam.',
      evidence=(
        'The `native-adb-package-review` scenario reports live source `{source}`.'.format(
          source=read_side_scenarios['native-adb-package-review']['live_source'],
        ),
        'The `fastboot-fallback-review` scenario reports live source `{source}`.'.format(
          source=read_side_scenarios['fastboot-fallback-review']['live_source'],
        ),
        'The `safe-path-ready-review` scenario now reports Samsung download-mode live source `{source}`.'.format(
          source=safe_path_ready_live_source,
        ),
        'The shared CLI inspect-only path now imports `VulcanUSBScanner` / `build_usb_live_detection_session` and no longer defaults supported-path Samsung identity to Heimdall detect.',
      ),
      next_actions=(
        ()
        if s6_02_status == 'implemented'
        else (
          'Replace the externally delegated Samsung download-mode detect/identity path with a Calamum-owned integrated path for the supported matrix; embedded Heimdall-derived internals remain acceptable only if the external dependency disappears.',
        )
      ),
      notes=(
        ('FS6-02 closes the supported-path detect/identity blocker while PIT and write/runtime closure remain in `S6-03` and `S6-04`.' ,)
        if s6_02_status == 'implemented'
        else ('This is real partial progress, not a green final-frame closeout.',)
      ),
    ),
    CriterionResult(
      sprint='0.6.0',
      criterion_id='S6-03',
      title='PIT retrieval is only partially autonomous even though PIT truth is repo-owned',
      status='partial',
      priority='high',
      impact='The platform already owns PIT interpretation and alignment policy, but still relies on an external Heimdall-backed path to retrieve the live PIT data used by the supported Samsung path.',
      evidence=(
        'The `native-adb-package-review` scenario keeps PIT state `{state}` with package alignment `{alignment}`.'.format(
          state=read_side_scenarios['native-adb-package-review']['pit_state'],
          alignment=read_side_scenarios['native-adb-package-review']['pit_package_alignment'],
        ),
        'The CLI main surface still imports `build_print_pit_command_plan` and `build_download_pit_command_plan` from `adapters.heimdall`.',
        'The safe-path ready review now starts from native USB download-mode identity, but bounded PIT capture still runs through Heimdall-backed print-pit / download-pit seams.',
      ),
      next_actions=(
        'Introduce a Calamum-owned integrated PIT acquisition path for the supported Samsung matrix while preserving the current repo-owned comparison/alignment contract.',
      ),
    ),
    CriterionResult(
      sprint='0.6.0',
      criterion_id='S6-04',
      title='Runtime governance and evidence are platform-owned, but live transfer autonomy is only partial',
      status='partial',
      priority='high',
      impact='The final frame can preserve current governance, progress, transcript, and reporting contracts, but the live write engine underneath them is still externally Heimdall-backed.',
      evidence=(
        'Ready execute evidence preserves the platform governance line `[SAFE-PATH] governance=platform_supervised ...`.',
        'Ready execute evidence preserves authority ownership `{owner}` and transport state `{state}`.'.format(
          owner=execute_ready_evidence['authority']['ownership'],
          state=execute_ready_evidence['transport']['state'],
        ),
        'Blocked execute control still shows `execution_allowed={allowed}` with transport state `{state}` before invocation.'.format(
          allowed=execute_blocked_control['execution_allowed'],
          state=execute_blocked_control['transport']['state'],
        ),
      ),
      next_actions=(
        'Keep the current safe-path governance/evidence shell, but replace the externally Heimdall-backed transfer runner with a Calamum-owned integrated Samsung runtime.',
        'Re-prove resume/progress/transcript behavior through an integrated-runtime closeout bundle.',
      ),
    ),
    CriterionResult(
      sprint='0.6.0',
      criterion_id='S6-05',
      title='Deferred publication posture and the `1.0.0` promotion gate are now explicit',
      status='implemented',
      priority='medium',
      impact='The final-frame work can now close autonomy first and let public-promotion proof happen in the dedicated `1.0.0` lane rather than forcing premature registry publication.',
      evidence=(
        'The master plan now has a `Revised packaging and publication cadence` section that defers renewed PyPI publication until the immediate post-`0.6.0` `1.0.0` promotion boundary.',
        'Sprint 6 authority docs now exist: {matches}.'.format(
          matches=', '.join(sprint6_doc_matches),
        ),
        'The promotion gate now exists: {matches}.'.format(
          matches=', '.join(promotion_gate_doc_matches),
        ),
      ),
    ),
  ]

  return tuple(criteria)


def _build_opportunistic_finds(context: Mapping[str, Any]) -> Tuple[Finding, ...]:
  return (
    Finding(
      finding_id='X-01',
      title='Executable closeout bundles already exist through Sprint 4',
      severity='medium',
      category='foundation',
      summary='The final-frame stack can inherit real execution/evidence surfaces instead of planning from a blank slate.',
      evidence=(
        'CLI help still exposes `--integration-suite`, and the audit generated `sprint-close`, `orchestration-close`, `read-side-close`, and `safe-path-close` directly from the live CLI.',
      ),
    ),
    Finding(
      finding_id='X-02',
      title='Governance, reporting, and export surfaces are already platform-owned',
      severity='medium',
      category='foundation',
      summary='The remaining hard work is concentrated on Samsung-native transport ownership rather than shell/reporting invention.',
      evidence=(
        'Ready execute evidence preserves the platform-supervised safe-path governance line and first-class authority/reporting objects.',
        'Blocked execute control still keeps the not-invoked transport and rejection reason explicit, which is the right shell contract to preserve during transport replacement.',
      ),
    ),
    Finding(
      finding_id='X-03',
      title='ADB and fastboot native read-side ownership already narrow the remaining transport problem',
      severity='medium',
      category='scope',
      summary='The final-frame stack does not need to replace every companion subsystem; it needs to close Samsung download-mode detect, PIT acquisition, and write transport.',
      evidence=(
        'The `native-adb-package-review` and `fastboot-fallback-review` scenarios both remain live in the `read-side-close` bundle.',
      ),
    ),
  )


def _build_deviations(context: Mapping[str, Any]) -> Tuple[Finding, ...]:
  current_repository_version = str(context.get('current_repository_version', '0.5.0'))
  public_stable_version = str(context.get('public_stable_version', '0.3.0'))
  return (
    Finding(
      finding_id='D-01',
      title='A green Sprint 4 audit is not a valid Sprint 5/6 schedule-alignment proof',
      severity='critical',
      category='scope-drift',
      summary='The older audit is scoped through `0.4.0`, so using its green result to justify Sprint 5 or Sprint 6 alignment would be a category error, not evidence.',
      evidence=(
        '`run_v040_timeline_audit.py` explicitly describes itself as auditing `through 0.4.0` and hardcodes `target_sprint=\'0.4.0\'`.',
      ),
    ),
    Finding(
      finding_id='D-02',
      title='The planning-surface gap is now closed, so the remaining drift is execution not authority',
      severity='medium',
      category='execution-gap',
      summary='Dedicated Sprint 5, Sprint 6, and `1.0.0` authority docs now exist, which means the remaining red items are runtime gaps rather than missing planning shells.',
      evidence=(
        'Nested-repo `docs/` now contains dedicated `0.5.0`, `0.6.0`, and `1.0.0` planning surfaces.',
      ),
    ),
    Finding(
      finding_id='D-03',
      title='Current repository release surfaces intentionally lag the planned Sprint 5 boundary',
      severity='medium',
      category='release-lag',
      summary='The repo-facing metadata now reflects the local `{current_version}` package boundary while the latest public stable release remains `{public_version}`, and under the revised roadmap that split is intentional until any later Sprint 5 repo-visible seal step and the post-`0.6.0` `1.0.0` promotion gate.'.format(
        current_version=current_repository_version,
        public_version=public_stable_version,
      ),
      evidence=(
        '`pyproject.toml` currently reports `{version}` as the repository package version.'.format(
          version=current_repository_version,
        ),
        '`README.md` now describes `{version}` as the local package-only Sprint 5 boundary while keeping `{public_version}` as the public stable release.'.format(
          version=current_repository_version,
          public_version=public_stable_version,
        ),
        '`CHANGELOG.md` now tops out at `{version}`, while `{public_version}` remains preserved as the latest public stable release section.'.format(
          version=current_repository_version,
          public_version=public_stable_version,
        ),
      ),
    ),
  )


def _build_sprint_counts(criteria: Sequence[CriterionResult]) -> Dict[str, Dict[str, int]]:
  counts = {
    sprint: {'implemented': 0, 'partial': 0, 'open': 0}
    for sprint in SPRINT_LABELS
  }
  for criterion in criteria:
    counts.setdefault(criterion.sprint, {'implemented': 0, 'partial': 0, 'open': 0})
    counts[criterion.sprint][criterion.status] += 1
  return counts


def _build_final_frame_closeout_map(
  criteria: Sequence[CriterionResult],
) -> Tuple[str, ...]:
  ordered_actions = []
  seen = set()
  for criterion in criteria:
    if criterion.sprint not in ('0.5.0', '0.6.0'):
      continue
    if criterion.status == 'implemented':
      continue
    for action in criterion.next_actions:
      if action in seen:
        continue
      seen.add(action)
      ordered_actions.append(action)
  return tuple(ordered_actions)


def _render_markdown(summary: AuditSummary) -> str:
  lines = [
    '# Calamum Vulcan `0.6.0` final-frame alignment audit',
    '',
    '- captured at: `{captured}`'.format(captured=summary.captured_at_utc),
    '- repo root: `{root}`'.format(root=summary.repo_root),
    '- output root: `{root}`'.format(root=summary.output_root),
    '- current repository package version: `{version}`'.format(version=summary.current_repository_version),
    '- target sprint: `{target}` — {label}'.format(
      target=summary.target_sprint,
      label=SPRINT_LABELS[summary.target_sprint],
    ),
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
      '## Final-frame closeout map',
      '',
    ]
  )
  for item in summary.final_frame_closeout_map:
    lines.append('- {item}'.format(item=item))
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
      '- `implemented` means the planned surface is materially present in the current workspace and was re-probed during this audit.',
      '- `partial` means meaningful platform ownership exists, but the final autonomy target is still materially unclosed.',
      '- `open` means the planned end-state is still absent for the current Sprint 5 / Sprint 6 target boundary.',
      '- current implementation probes are status evidence only; the planning surfaces remain the authority for sprint meaning and target semantics.',
      '- lower-sprint greens are retained as historical implementation evidence only; they are not treated as substitute proof for Sprint 5 or Sprint 6 alignment.',
      '',
    ]
  )
  return '\n'.join(lines)


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description='Audit the current Calamum Vulcan implementation against the 0.6.0 final-frame autonomy target.',
  )
  parser.add_argument(
    '--output-root',
    default=str(DEFAULT_OUTPUT_ROOT),
    help='Directory where the audit report and raw probe outputs should be written.',
  )
  parser.add_argument(
    '--captured-at-utc',
    default='2026-04-21T00:00:00Z',
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
  plan_text = _read_text(PLAN_PATH)
  sprint6_execution_surface_text = _read_text(SPRINT6_EXECUTION_SURFACE_PATH)
  sprint6_checklist_text = _read_text(SPRINT6_CHECKLIST_PATH)
  app_main_text = _read_text(APP_MAIN_PATH)
  demo_text = _read_text(APP_DEMO_PATH)
  integration_text = _read_text(APP_INTEGRATION_PATH)
  safe_path_text = _read_text(SAFE_PATH_MODEL_PATH)
  v040_audit_text = _read_text(V040_AUDIT_PATH)
  sprint5_doc_matches = _doc_matches('*0.5.0*.md')
  sprint6_doc_matches = _doc_matches('*0.6.0*.md')
  promotion_gate_doc_matches = _doc_matches('*1.0.0*Promotion_Gate*.md')
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

  raw_probe_summary = {
    'transport_sources': available_transport_sources(),
    'sprint5_doc_matches': sprint5_doc_matches,
    'sprint6_doc_matches': sprint6_doc_matches,
    'promotion_gate_doc_matches': promotion_gate_doc_matches,
    'current_repository_version': pyproject['project']['version'],
    'sprint6_support_contract_markers': {
      'supported_path_sequence': 'detect -> PIT -> package-aligned execution -> transcript/evidence -> recovery/resume' in sprint6_execution_surface_text,
      'integrated_runtime_token_present': 'integrated-runtime' in available_transport_sources(),
      'blocker_inventory_present': 'Current blocker inventory frozen by `FS6-01`' in sprint6_checklist_text,
    },
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
    'safe_path_ready_review': _scenario_map(bundles['safe-path-close'])['safe-path-ready-review'],
    'safe_path_runtime_complete': _scenario_map(bundles['safe-path-close'])['safe-path-runtime-complete'],
    'native_adb_package_review': _scenario_map(bundles['read-side-close'])['native-adb-package-review'],
    'fastboot_fallback_review': _scenario_map(bundles['read-side-close'])['fastboot-fallback-review'],
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
  }
  _write_json(raw_root / 'probe_summary.json', raw_probe_summary)
  _append_progress(progress_path, 'wrote_probe_summary')

  context = {
    'pyproject': pyproject,
    'readme_text': readme_text,
    'changelog_text': changelog_text,
    'plan_text': plan_text,
    'sprint6_execution_surface_text': sprint6_execution_surface_text,
    'sprint6_checklist_text': sprint6_checklist_text,
    'app_main_text': app_main_text,
    'demo_text': demo_text,
    'integration_text': integration_text,
    'safe_path_text': safe_path_text,
    'v040_audit_text': v040_audit_text,
    'cli_help': cli_help,
    'bundles': bundles,
    'bundle_markdown': bundle_markdown,
    'transport_sources': available_transport_sources(),
    'sprint5_doc_matches': sprint5_doc_matches,
    'sprint6_doc_matches': sprint6_doc_matches,
    'promotion_gate_doc_matches': promotion_gate_doc_matches,
    'execute_ready_control': execute_ready_control,
    'execute_ready_evidence': execute_ready_evidence,
    'execute_blocked_control': execute_blocked_control,
    'current_repository_version': str(pyproject['project']['version']),
    'public_stable_version': '0.3.0',
  }

  criteria = _build_criteria(context)
  opportunistic_finds = _build_opportunistic_finds(context)
  deviations = _build_deviations(context)
  final_frame_closeout_map = _build_final_frame_closeout_map(criteria)
  status_counts = dict(Counter(criterion.status for criterion in criteria))
  sprint_counts = _build_sprint_counts(criteria)
  summary = AuditSummary(
    captured_at_utc=args.captured_at_utc,
    repo_root=str(REPO_ROOT),
    output_root=str(output_root),
    current_repository_version=str(pyproject['project']['version']),
    target_sprint='0.6.0',
    criteria=criteria,
    opportunistic_finds=opportunistic_finds,
    deviations=deviations,
    final_frame_closeout_map=final_frame_closeout_map,
    command_captures=tuple(command_captures),
    status_counts=status_counts,
    sprint_counts=sprint_counts,
    raw_probe_summary=raw_probe_summary,
  )

  json_path = output_root / 'v060_alignment_audit.json'
  markdown_path = output_root / 'v060_alignment_audit.md'
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
      'final_frame_actions="{count}"'.format(count=len(final_frame_closeout_map)),
    ]
  )
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
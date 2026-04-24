"""Run the Sprint 0.6.0 multi-strategy readiness stack for Calamum Vulcan."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from scripts.readiness_reporting import write_readiness_aggregate_report


ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'fs6_readiness'


@dataclass(frozen=True)
class ValidationLane:
  """One runnable validation lane in the Sprint 6 readiness stack."""

  name: str
  category: str
  description: str
  command: Tuple[str, ...]
  evidence_hint: str


@dataclass(frozen=True)
class ValidationLaneResult:
  """Serializable summary for one readiness lane execution."""

  name: str
  category: str
  description: str
  command: Tuple[str, ...]
  evidence_hint: str
  status: str
  returncode: int
  stdout_path: str
  stderr_path: str


def build_default_lanes() -> Tuple[ValidationLane, ...]:
  """Return the default ordered Sprint 6 readiness lanes."""

  python_executable = sys.executable
  return (
    ValidationLane(
      name='targeted_sprint6_closure_slice',
      category='pytest',
      description='Run the targeted Sprint 6 closure slice for USB, PIT, CLI, Qt, reporting, bundle, and audit seams.',
      command=(
        python_executable,
        '-m',
        'pytest',
        'tests/unit/test_usb_scanner.py',
        'tests/unit/test_live_device_contract.py',
        'tests/unit/test_pit_contract.py',
        'tests/unit/test_cli_control_surface.py',
        'tests/unit/test_qt_shell_contract.py',
        'tests/unit/test_reporting_contract.py',
        'tests/unit/test_integration_suite.py',
        'tests/unit/test_sprint_audit_metadata.py',
        'tests/unit/test_v060_readiness_stack.py',
        '-q',
      ),
      evidence_hint='Focused Sprint 6 closure proof across native USB, PIT, CLI, Qt, reporting, bundle, and audit surfaces.',
    ),
    ValidationLane(
      name='pytest_baseline',
      category='pytest',
      description='Run the full source-tree pytest unit baseline.',
      command=(python_executable, '-m', 'pytest', 'tests/unit', '-q'),
      evidence_hint='Full source-tree contract and unit proof.',
    ),
    ValidationLane(
      name='aggressive_penetration_pytest',
      category='penetration',
      description='Run the adversarial pytest slice for security, package, PIT, and runtime-dependency boundaries.',
      command=(
        python_executable,
        '-m',
        'pytest',
        'tests/unit/test_security_validation.py',
        'tests/unit/test_package_importer.py',
        'tests/unit/test_package_snapshot.py',
        'tests/unit/test_pit_contract.py',
        'tests/unit/test_runtime_dependencies.py',
        '-q',
      ),
      evidence_hint='Aggressive penetration-style pytest slice for package, parser, PIT, and runtime-dependency boundaries.',
    ),
    ValidationLane(
      name='aggressive_penetration_suite',
      category='penetration',
      description='Run the shared security validation suite for dangerous-pattern, fallback-quarantine, and transcript boundaries.',
      command=(python_executable, 'scripts/run_security_validation_suite.py'),
      evidence_hint='Security validation artifacts under temp/security_validation/.',
    ),
    ValidationLane(
      name='v060_alignment_audit',
      category='audit',
      description='Run the Sprint 6 alignment audit against the live autonomy-close candidate surfaces.',
      command=(python_executable, 'scripts/run_v060_alignment_audit.py'),
      evidence_hint='Sprint 6 alignment audit proof under temp/v060_alignment_audit/.',
    ),
    ValidationLane(
      name='build_artifacts',
      category='sandbox',
      description='Refresh the wheel and sdist while enforcing the artifact contract.',
      command=(python_executable, 'scripts/build_release_artifacts.py'),
      evidence_hint='Artifact contract proof under temp/fs_p02_build_artifacts/.',
    ),
    ValidationLane(
      name='sandbox_installed_artifact',
      category='sandbox',
      description='Validate the installed-artifact contract from an isolated install root.',
      command=(python_executable, 'scripts/validate_installed_artifact.py'),
      evidence_hint='Installed-artifact proof in temp and %TEMP% validation roots.',
    ),
    ValidationLane(
      name='scripted_simulation',
      category='scripted',
      description='Run the deterministic scripted simulation suite across source and installed contexts.',
      command=(python_executable, 'scripts/run_scripted_simulation_suite.py'),
      evidence_hint='Scripted simulation proof under temp/fs_p04_scripted_simulation/.',
    ),
    ValidationLane(
      name='smoke_empirical_review',
      category='smoke',
      description='Run the packaged GUI and evidence smoke review stack before any live empirical approval pass.',
      command=(python_executable, 'scripts/run_empirical_review_stack.py'),
      evidence_hint='Packaged GUI smoke-review proof under temp/fs_p05_empirical_review/.',
    ),
  )


def _print(lines: Iterable[str]) -> None:
  for line in lines:
    print(line)


def _run_lane(lane: ValidationLane) -> ValidationLaneResult:
  lane_root = ARCHIVE_ROOT / lane.name
  lane_root.mkdir(parents=True, exist_ok=True)
  stdout_path = lane_root / 'stdout.txt'
  stderr_path = lane_root / 'stderr.txt'
  print('start_lane="{name}" category="{category}"'.format(
    name=lane.name,
    category=lane.category,
  ))
  result = subprocess.run(
    lane.command,
    cwd=REPO_ROOT,
    capture_output=True,
    text=True,
  )
  stdout_path.write_text(result.stdout, encoding='utf-8')
  stderr_path.write_text(result.stderr, encoding='utf-8')
  status = 'passed' if result.returncode == 0 else 'failed'
  print('finish_lane="{name}" status="{status}" returncode="{returncode}"'.format(
    name=lane.name,
    status=status,
    returncode=result.returncode,
  ))
  return ValidationLaneResult(
    name=lane.name,
    category=lane.category,
    description=lane.description,
    command=lane.command,
    evidence_hint=lane.evidence_hint,
    status=status,
    returncode=result.returncode,
    stdout_path=str(stdout_path),
    stderr_path=str(stderr_path),
  )


def _render_markdown_summary(summary: Mapping[str, object]) -> str:
  lines = [
    '# Sprint 0.6.0 readiness summary',
    '',
    '- repo root: `{root}`'.format(root=summary['repo_root']),
    '- overall status: `{status}`'.format(status=summary['overall_status']),
    '- ready for live empirical: `{status}`'.format(
      status=summary['ready_for_live_empirical'],
    ),
    '- publication rehearsal deferred: `True`',
    '',
    '## Lane results',
    '',
  ]
  for lane in summary['lanes']:
    command = ' '.join(lane['command'])
    lines.extend(
      [
        '### `{name}`'.format(name=lane['name']),
        '',
        '- category: `{category}`'.format(category=lane['category']),
        '- status: `{status}`'.format(status=lane['status']),
        '- command: `{command}`'.format(command=command),
        '- evidence: {hint}'.format(hint=lane['evidence_hint']),
        '- stdout: `{path}`'.format(path=lane['stdout_path']),
        '- stderr: `{path}`'.format(path=lane['stderr_path']),
        '',
      ]
    )
  lines.extend(
    [
      '## Readiness interpretation',
      '',
      '- `passed` means the selected Sprint 6 readiness lanes all completed successfully and the package-only autonomy candidate is materially coherent.',
      '- `failed` means at least one selected lane failed and Sprint 6 readiness should be treated as blocked until the failing lane is resolved or intentionally skipped with rationale.',
      '- `ready_for_live_empirical=True` means the automated pytest, penetration, audit, sandbox, scripted, and packaged smoke lanes all passed, so a manual live empirical pass is now justified.',
      '- renewed TestPyPI/PyPI rehearsal remains intentionally deferred to the immediate post-`0.6.0` `1.0.0` promotion gate.',
      '',
      '## Strategy coverage',
      '',
      '- `pytest`: focused Sprint 6 closure proof plus full contract baseline',
      '- `penetration`: aggressive penetration-style archive, parser, runtime-dependency, and security-boundary checks',
      '- `audit`: live Sprint 6 alignment verification against the autonomy contract',
      '- `sandbox`: built-artifact and isolated-install validation',
      '- `scripted`: deterministic scenario-matrix and bundle proof',
      '- `smoke`: packaged GUI launch, screenshot, and evidence-readability smoke proof',
      '',
    ]
  )
  return '\n'.join(lines)


def _write_summary(results: Sequence[ValidationLaneResult]) -> Dict[str, object]:
  overall_status = 'passed' if all(result.status == 'passed' for result in results) else 'failed'
  summary = {
    'repo_root': str(REPO_ROOT),
    'archive_root': str(ARCHIVE_ROOT),
    'aggregate_report_path': str(ARCHIVE_ROOT / 'readiness_aggregate_report.md'),
    'include_testpypi_rehearsal': False,
    'overall_status': overall_status,
    'ready_for_live_empirical': overall_status == 'passed',
    'promotion_gate_deferred': True,
    'lanes': [asdict(result) for result in results],
  }
  (ARCHIVE_ROOT / 'readiness_summary.json').write_text(
    json.dumps(summary, indent=2, sort_keys=True) + '\n',
    encoding='utf-8',
  )
  (ARCHIVE_ROOT / 'readiness_summary.md').write_text(
    _render_markdown_summary(summary) + '\n',
    encoding='utf-8',
  )
  write_readiness_aggregate_report(
    summary,
    archive_root=ARCHIVE_ROOT,
    repo_root=REPO_ROOT,
    sprint_label='0.6.0',
  )
  return summary


def main(argv: Optional[Sequence[str]] = None) -> int:
  del argv
  if ARCHIVE_ROOT.exists():
    shutil.rmtree(ARCHIVE_ROOT)
  ARCHIVE_ROOT.mkdir(parents=True)

  lanes = build_default_lanes()
  results = []
  for lane in lanes:
    result = _run_lane(lane)
    results.append(result)

  summary = _write_summary(tuple(results))
  _print(
    [
      'archive_root="{root}"'.format(root=ARCHIVE_ROOT),
      'aggregate_report="{path}"'.format(
        path=summary['aggregate_report_path'],
      ),
      'selected_lane_count="{count}"'.format(count=len(results)),
      'overall_status="{status}"'.format(status=summary['overall_status']),
      'ready_for_live_empirical="{status}"'.format(
        status=summary['ready_for_live_empirical'],
      ),
      'readiness_contract="{status}"'.format(status=summary['overall_status']),
    ]
  )
  return 0 if summary['overall_status'] == 'passed' else 1


if __name__ == '__main__':
  raise SystemExit(main())

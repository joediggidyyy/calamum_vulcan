"""Run the Sprint 0.5.0 multi-strategy readiness stack for Calamum Vulcan."""

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
ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'fs5_readiness'


@dataclass(frozen=True)
class ValidationLane:
  """One runnable validation lane in the Sprint 5 readiness stack."""

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


def build_default_lanes(include_testpypi: bool = False) -> Tuple[ValidationLane, ...]:
  """Return the default ordered Sprint 5 readiness lanes."""

  python_executable = sys.executable
  lanes = [
    ValidationLane(
      name='pytest_baseline',
      category='pytest',
      description='Run the full source-tree pytest unit baseline.',
      command=(python_executable, '-m', 'pytest', 'tests/unit', '-q'),
      evidence_hint='Source-tree contract and unit proof.',
    ),
    ValidationLane(
      name='aggressive_penetration_pytest',
      category='penetration',
      description='Run the adversarial pytest slice for security, archive, drift, and malformed-input boundaries.',
      command=(
        python_executable,
        '-m',
        'pytest',
        'tests/unit/test_security_validation.py',
        'tests/unit/test_package_importer.py',
        'tests/unit/test_package_snapshot.py',
        'tests/unit/test_pit_contract.py',
        '-q',
      ),
      evidence_hint='Aggressive penetration-style pytest slice.',
    ),
    ValidationLane(
      name='aggressive_penetration_suite',
      category='penetration',
      description='Run the shared security validation suite for dangerous-pattern, fallback-visibility, and transcript boundaries.',
      command=(python_executable, 'scripts/run_security_validation_suite.py'),
      evidence_hint='Security validation artifacts under temp/security_validation/.',
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
      evidence_hint='Scripted simulation proof under temp/fs_p05_scripted_simulation/.',
    ),
    ValidationLane(
      name='empirical_review',
      category='empirical',
      description='Run the packaged GUI and evidence empirical review stack.',
      command=(python_executable, 'scripts/run_empirical_review_stack.py'),
      evidence_hint='Empirical review proof under temp/fs_p05_empirical_review/.',
    ),
  ]
  if include_testpypi:
    lanes.append(
      ValidationLane(
        name='testpypi_rehearsal',
        category='release',
        description='Run the TestPyPI rehearsal and registry-delivered install proof.',
        command=(python_executable, 'scripts/run_testpypi_rehearsal.py'),
        evidence_hint='Registry rehearsal proof under temp/fs_p06_testpypi_rehearsal/.',
      )
    )
  return tuple(lanes)


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
    '# Sprint 0.5.0 readiness summary',
    '',
    '- repo root: `{root}`'.format(root=summary['repo_root']),
    '- overall status: `{status}`'.format(status=summary['overall_status']),
    '- include TestPyPI rehearsal: `{value}`'.format(
      value=summary['include_testpypi_rehearsal'],
    ),
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
      '- `passed` means the selected Sprint 5 readiness lanes all completed successfully.',
      '- `failed` means at least one selected lane failed and Sprint 5 readiness should be treated as blocked until the failing lane is resolved or intentionally skipped with rationale.',
      '',
      '## Strategy coverage',
      '',
      '- `pytest`: baseline contract coverage',
      '- `penetration`: aggressive penetration-style archive, drift, malformed-input, and security-boundary checks',
      '- `sandbox`: packaged-artifact and isolated-install validation',
      '- `scripted`: deterministic scenario-matrix proof',
      '- `empirical`: packaged GUI and evidence readability review',
      '- `release`: registry rehearsal when explicitly enabled',
      '',
    ]
  )
  return '\n'.join(lines)


def _write_summary(results: Sequence[ValidationLaneResult], include_testpypi: bool) -> Dict[str, object]:
  overall_status = 'passed' if all(result.status == 'passed' for result in results) else 'failed'
  summary = {
    'repo_root': str(REPO_ROOT),
    'archive_root': str(ARCHIVE_ROOT),
    'include_testpypi_rehearsal': include_testpypi,
    'overall_status': overall_status,
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
  return summary


def _parse_args(argv: Optional[Sequence[str]] = None) -> Dict[str, bool]:
  include_testpypi = '--include-testpypi' in (argv or sys.argv[1:])
  return {
    'include_testpypi': include_testpypi,
  }


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = _parse_args(argv)
  include_testpypi = args['include_testpypi']

  if ARCHIVE_ROOT.exists():
    shutil.rmtree(ARCHIVE_ROOT)
  ARCHIVE_ROOT.mkdir(parents=True)

  lanes = build_default_lanes(include_testpypi=include_testpypi)
  results = []
  for lane in lanes:
    result = _run_lane(lane)
    results.append(result)

  summary = _write_summary(tuple(results), include_testpypi=include_testpypi)
  _print(
    [
      'archive_root="{root}"'.format(root=ARCHIVE_ROOT),
      'selected_lane_count="{count}"'.format(count=len(results)),
      'overall_status="{status}"'.format(status=summary['overall_status']),
      'readiness_contract="{status}"'.format(status=summary['overall_status']),
    ]
  )
  return 0 if summary['overall_status'] == 'passed' else 1


if __name__ == '__main__':
  raise SystemExit(main())

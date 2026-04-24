"""Shared aggregate reporting helpers for readiness-stack runners."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Mapping
from typing import Optional
from typing import Tuple


def _generated_on_value(generated_on: Optional[str]) -> str:
  """Return the display date for a generated readiness report."""

  if generated_on is not None:
    return generated_on
  return datetime.now(timezone.utc).date().isoformat()


def _coerce_path(value: object) -> Optional[Path]:
  """Return one ``Path`` when the provided value is a non-empty string."""

  if not isinstance(value, str) or not value:
    return None
  return Path(value)


def _display_path(path: Path, repo_root: Path) -> str:
  """Return one repo-relative display path when possible."""

  try:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()
  except ValueError:
    return str(path)


def _collect_artifact_inventory(
  archive_root: Path,
  repo_root: Path,
) -> Tuple[Tuple[str, int], ...]:
  """Return the sorted report-artifact inventory for one readiness archive."""

  if not archive_root.exists():
    return ()
  inventory = []
  for artifact_path in sorted(archive_root.rglob('*')):
    if artifact_path.is_file():
      if artifact_path.name == 'readiness_aggregate_report.md':
        continue
      inventory.append(
        (_display_path(artifact_path, repo_root), artifact_path.stat().st_size)
      )
  return tuple(inventory)


def _read_excerpt(path: Optional[Path], failed: bool) -> Tuple[str, ...]:
  """Return a bounded excerpt from one report file."""

  if path is None or not path.exists():
    return ('(file missing)',)
  lines = tuple(
    line.rstrip()
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines()
    if line.strip()
  )
  if not lines:
    return ('(empty)',)
  if failed:
    return lines[-10:]
  return lines[:6]


def render_readiness_aggregate_report(
  summary: Mapping[str, object],
  archive_root: Path,
  repo_root: Path,
  sprint_label: str,
  generated_on: Optional[str] = None,
) -> str:
  """Render one aggregate readiness report with the summary at the top."""

  lanes = tuple(summary.get('lanes', ()))
  passed_lanes = tuple(
    lane for lane in lanes if lane.get('status') == 'passed'
  )
  failed_lanes = tuple(
    lane for lane in lanes if lane.get('status') != 'passed'
  )
  artifact_inventory = _collect_artifact_inventory(archive_root, repo_root)
  summary_path = archive_root / 'readiness_summary.md'

  lines = [
    '# Sprint {label} readiness aggregate report'.format(label=sprint_label),
    '',
    '- generated: `{generated}`'.format(
      generated=_generated_on_value(generated_on),
    ),
    '- repo root: `{root}`'.format(root=repo_root),
    '- source archive: `{path}/`'.format(
      path=_display_path(archive_root, repo_root),
    ),
    '- source summary: `{path}`'.format(
      path=_display_path(summary_path, repo_root),
    ),
    '',
    '## Summary',
    '',
    '- overall readiness contract: **`{status}`**'.format(
      status=summary.get('overall_status', 'unknown'),
    ),
    '- ready for live empirical: **`{status}`**'.format(
      status=summary.get('ready_for_live_empirical', 'unknown'),
    ),
    '- include TestPyPI rehearsal: `{value}`'.format(
      value=summary.get('include_testpypi_rehearsal', False),
    ),
    '- verified report artifacts on disk: **{count}**'.format(
      count=len(artifact_inventory),
    ),
    '- passing lanes: **{passed} / {total}**'.format(
      passed=len(passed_lanes),
      total=len(lanes),
    ),
    '- failing lanes: **{failed} / {total}**'.format(
      failed=len(failed_lanes),
      total=len(lanes),
    ),
  ]
  if failed_lanes:
    lines.append(
      '- failing lane set: {names}'.format(
        names=', '.join(
          '`{name}`'.format(name=lane.get('name', 'unknown'))
          for lane in failed_lanes
        ),
      )
    )
  lines.extend(
    [
      '',
      '## Lane result summary',
      '',
      '| Lane | Category | Status | Command |',
      '| --- | --- | --- | --- |',
    ]
  )
  for lane in lanes:
    lines.append(
      '| `{name}` | `{category}` | `{status}` | `{command}` |'.format(
        name=lane.get('name', 'unknown'),
        category=lane.get('category', 'unknown'),
        status=lane.get('status', 'unknown'),
        command=' '.join(lane.get('command', ())),
      )
    )

  if failed_lanes:
    lines.extend(
      [
        '',
        '## Failing lane excerpts',
        '',
      ]
    )
    for lane in failed_lanes:
      stdout_path = _coerce_path(lane.get('stdout_path'))
      stderr_path = _coerce_path(lane.get('stderr_path'))
      stdout_excerpt = _read_excerpt(stdout_path, failed=True)
      stderr_excerpt = _read_excerpt(stderr_path, failed=True)
      lines.extend(
        [
          '### `{name}`'.format(name=lane.get('name', 'unknown')),
          '',
          '- return code: `{code}`'.format(
            code=lane.get('returncode', 'unknown'),
          ),
          '- stdout: `{path}`'.format(
            path=(
              _display_path(stdout_path, repo_root)
              if stdout_path is not None
              else 'missing'
            ),
          ),
          '- stderr: `{path}`'.format(
            path=(
              _display_path(stderr_path, repo_root)
              if stderr_path is not None
              else 'missing'
            ),
          ),
          '',
          '```text',
          *stdout_excerpt,
          '```',
        ]
      )
      if stderr_excerpt != ('(empty)',):
        lines.extend(
          [
            '',
            '```text',
            *stderr_excerpt,
            '```',
          ]
        )
      else:
        lines.append('')
        lines.append('- stderr excerpt: _(empty)_')
      lines.append('')

  lines.extend(
    [
      '## Verified report artifacts on disk',
      '',
      '| Artifact | Size (bytes) |',
      '| --- | ---: |',
    ]
  )
  for relative_path, size in artifact_inventory:
    lines.append('| `{path}` | {size} |'.format(path=relative_path, size=size))

  lines.extend(
    [
      '',
      '## Lane output highlights',
      '',
    ]
  )
  for lane in lanes:
    stdout_path = _coerce_path(lane.get('stdout_path'))
    stderr_path = _coerce_path(lane.get('stderr_path'))
    failed = lane.get('status') != 'passed'
    stdout_excerpt = _read_excerpt(stdout_path, failed=failed)
    stderr_excerpt = _read_excerpt(stderr_path, failed=failed)
    lines.extend(
      [
        '### `{name}`'.format(name=lane.get('name', 'unknown')),
        '',
        '- status: `{status}`'.format(status=lane.get('status', 'unknown')),
        '- evidence: {hint}'.format(
          hint=lane.get('evidence_hint', 'No evidence hint recorded.'),
        ),
        '- stdout: `{path}`'.format(
          path=(
            _display_path(stdout_path, repo_root)
            if stdout_path is not None
            else 'missing'
          ),
        ),
        '- stderr: `{path}`'.format(
          path=(
            _display_path(stderr_path, repo_root)
            if stderr_path is not None
            else 'missing'
          ),
        ),
        '',
        '```text',
        *stdout_excerpt,
        '```',
      ]
    )
    if stderr_excerpt == ('(empty)',):
      lines.extend(['', '- stderr excerpt: _(empty)_', ''])
    else:
      lines.extend(['', '```text', *stderr_excerpt, '```', ''])

  lines.extend(
    [
      '## Aggregate conclusion',
      '',
      'This aggregate report is the runner-owned convenience surface for the current readiness archive. The raw `stdout.txt` / `stderr.txt` pairs and the `readiness_summary.json` / `.md` files remain the authoritative lane artifacts for detailed audit work.',
    ]
  )
  return '\n'.join(lines)


def write_readiness_aggregate_report(
  summary: Mapping[str, object],
  archive_root: Path,
  repo_root: Path,
  sprint_label: str,
  generated_on: Optional[str] = None,
) -> Path:
  """Write one aggregate readiness report to the readiness archive."""

  report_path = archive_root / 'readiness_aggregate_report.md'
  report_path.write_text(
    render_readiness_aggregate_report(
      summary,
      archive_root=archive_root,
      repo_root=repo_root,
      sprint_label=sprint_label,
      generated_on=generated_on,
    )
    + '\n',
    encoding='utf-8',
  )
  return report_path
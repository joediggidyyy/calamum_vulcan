"""Prepare the Sprint 0.6.0 live empirical review lane for manual approval."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Mapping
from typing import Optional
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.adapters.heimdall import HeimdallRuntimeProbe
from calamum_vulcan.adapters.heimdall import probe_heimdall_runtime
from calamum_vulcan.usb.scanner import USBProbeResult
from calamum_vulcan.usb.scanner import VulcanUSBScanner


ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'fs6_live_empirical'
MANUAL_REVIEW_ROOT = ARCHIVE_ROOT / 'manual_review'
INTERACTIVE_ARTIFACT_ROOT = ARCHIVE_ROOT / 'interactive'
DEFAULT_GUI_SCENARIO = 'no-device'


def _project_version() -> str:
  """Return the current package version from pyproject.toml."""

  with (REPO_ROOT / 'pyproject.toml').open('rb') as handle:
    project = tomllib.load(handle)['project']
  return str(project['version'])


CURRENT_PACKAGE_VERSION = _project_version()


def _utc_timestamp() -> str:
  """Return one filesystem-safe UTC timestamp."""

  return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _json_ready_runtime_probe(probe: HeimdallRuntimeProbe) -> Mapping[str, object]:
  """Return a JSON-serializable runtime probe payload."""

  return {
    'executable_name': probe.executable_name,
    'resolved_path': probe.resolved_path,
    'resolution_source': probe.resolution_source,
    'packaged_candidate': probe.packaged_candidate,
    'packaged_candidate_present': probe.packaged_candidate_present,
    'smoke_test_exit_code': probe.smoke_test_exit_code,
    'smoke_test_summary': probe.smoke_test_summary,
    'stdout_lines': list(probe.stdout_lines),
    'stderr_lines': list(probe.stderr_lines),
    'available': probe.available,
  }


def _json_ready_usb_probe(probe: USBProbeResult) -> Mapping[str, object]:
  """Return a JSON-serializable native USB probe payload."""

  return {
    'state': probe.state,
    'summary': probe.summary,
    'notes': list(probe.notes),
    'device_count': len(probe.devices),
    'remediation_command': probe.remediation_command,
  }


def _gui_launch_command(
  python_executable: str,
  duration_ms: int = 0,
) -> tuple[str, ...]:
  """Return the preferred GUI launch command for the manual review lane."""

  command = [
    python_executable,
    '-m',
    'calamum_vulcan.app',
    '--scenario',
    DEFAULT_GUI_SCENARIO,
  ]
  if duration_ms > 0:
    command.extend(['--duration-ms', str(duration_ms)])
  return tuple(command)


def _summary_notes(
  runtime_probe: HeimdallRuntimeProbe,
  usb_probe: USBProbeResult,
) -> list[str]:
  """Return one deduplicated note list for manual empirical readiness."""

  notes = []
  for value in (
    runtime_probe.smoke_test_summary,
    *runtime_probe.stderr_lines,
    usb_probe.summary,
    *usb_probe.notes,
  ):
    if value and value not in notes:
      notes.append(value)
  return notes


def build_manual_empirical_summary(
  runtime_probe: HeimdallRuntimeProbe,
  usb_probe: USBProbeResult,
  review_root: Path,
  python_executable: str,
  duration_ms: int = 0,
) -> dict[str, object]:
  """Return the manual empirical readiness summary payload."""

  gui_launch_command = _gui_launch_command(
    python_executable,
    duration_ms=duration_ms,
  )
  ready = runtime_probe.available and usb_probe.state != 'failed'
  return {
    'package_version': CURRENT_PACKAGE_VERSION,
    'status': 'ready' if ready else 'blocked',
    'repo_root': str(REPO_ROOT),
    'archive_root': str(ARCHIVE_ROOT),
    'review_root': str(review_root),
    'interactive_artifact_root': str(INTERACTIVE_ARTIFACT_ROOT),
    'runtime_probe': _json_ready_runtime_probe(runtime_probe),
    'usb_probe': _json_ready_usb_probe(usb_probe),
    'gui_launch_command': list(gui_launch_command),
    'notes': _summary_notes(runtime_probe, usb_probe),
    'next_steps': (
      [
        'Launch the GUI with the command below.',
        'Put the reviewed Samsung device into download mode.',
        'Run Detect device -> Read PIT and confirm the control deck stays on-frame and the blocker language stays specific.',
        'Archive screenshots plus any interactive blocker artifacts under the review root before signoff.',
      ]
      if ready else
      [
        'Resolve the blocking runtime notes listed below.',
        'Rerun this preflight until status=ready before spending another manual approval pass.',
      ]
    ),
  }


def render_manual_empirical_markdown(summary: Mapping[str, object]) -> str:
  """Render the manual empirical readiness summary as Markdown."""

  runtime_probe = summary['runtime_probe']
  usb_probe = summary['usb_probe']
  gui_launch_command = ' '.join(summary['gui_launch_command'])
  lines = [
    '# Sprint 0.6.0 live empirical preflight',
    '',
    '- package version: `{version}`'.format(version=summary['package_version']),
    '- status: `{status}`'.format(status=summary['status']),
    '- review root: `{root}`'.format(root=summary['review_root']),
    '- interactive artifact root: `{root}`'.format(
      root=summary['interactive_artifact_root'],
    ),
    '',
    '## Runtime probe',
    '',
    '- resolution source: `{source}`'.format(
      source=runtime_probe['resolution_source'],
    ),
    '- resolved path: `{path}`'.format(path=runtime_probe['resolved_path']),
    '- packaged candidate present: `{present}`'.format(
      present=runtime_probe['packaged_candidate_present'],
    ),
    '- smoke test exit code: `{code}`'.format(
      code=runtime_probe['smoke_test_exit_code'],
    ),
    '- summary: {summary}'.format(
      summary=runtime_probe['smoke_test_summary'],
    ),
    '',
    '## Native USB backend',
    '',
    '- state: `{state}`'.format(state=usb_probe['state']),
    '- summary: {summary}'.format(summary=usb_probe['summary']),
    '- device count during preflight: `{count}`'.format(
      count=usb_probe['device_count'],
    ),
    '',
    '## Manual launch command',
    '',
    '`{command}`'.format(command=gui_launch_command),
    '',
    '## Next steps',
    '',
  ]
  for step in summary['next_steps']:
    lines.append('- ' + step)
  if summary['notes']:
    lines.extend(['', '## Notes', ''])
    for note in summary['notes']:
      lines.append('- ' + note)
  return '\n'.join(lines)


def _write_summary_files(summary: Mapping[str, object], review_root: Path) -> None:
  """Write the JSON and Markdown readiness summaries."""

  review_root.mkdir(parents=True, exist_ok=True)
  (review_root / 'live_empirical_preflight.json').write_text(
    json.dumps(summary, indent=2, sort_keys=True) + '\n',
    encoding='utf-8',
  )
  (review_root / 'live_empirical_preflight.md').write_text(
    render_manual_empirical_markdown(summary) + '\n',
    encoding='utf-8',
  )


def _launch_gui(
  command: Sequence[str],
) -> None:
  """Launch the interactive GUI host for the manual review lane."""

  subprocess.Popen(
    command,
    cwd=REPO_ROOT,
    close_fds=True,
  )


def main(argv: Optional[Sequence[str]] = None) -> int:
  """Prepare the manual empirical review lane and optionally launch the GUI."""

  parser = argparse.ArgumentParser(
    description='Prepare the Sprint 0.6.0 live empirical review lane.',
  )
  parser.add_argument(
    '--launch-gui',
    action='store_true',
    help='Launch the GUI automatically after the readiness preflight passes.',
  )
  parser.add_argument(
    '--duration-ms',
    type=int,
    default=0,
    help='Optional duration bound forwarded to the GUI launch command.',
  )
  args = parser.parse_args(argv)

  review_root = MANUAL_REVIEW_ROOT / _utc_timestamp()
  runtime_probe = probe_heimdall_runtime()
  usb_probe = VulcanUSBScanner().probe_download_mode_devices()
  summary = build_manual_empirical_summary(
    runtime_probe,
    usb_probe,
    review_root,
    sys.executable,
    duration_ms=args.duration_ms,
  )
  _write_summary_files(summary, review_root)

  print('review_root="{root}"'.format(root=review_root))
  print('status="{status}"'.format(status=summary['status']))
  print(
    'gui_launch_command="{command}"'.format(
      command=' '.join(summary['gui_launch_command']),
    )
  )

  if args.launch_gui and summary['status'] == 'ready':
    _launch_gui(summary['gui_launch_command'])
    print('gui_launch="started"')

  return 0 if summary['status'] == 'ready' else 1


if __name__ == '__main__':
  raise SystemExit(main())

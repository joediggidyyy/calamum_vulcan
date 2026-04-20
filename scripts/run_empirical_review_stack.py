"""Run the FS-P05 empirical review and public-doc readiness stack."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from typing import Mapping
from typing import Optional
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.validation import run_security_validation_suite
from calamum_vulcan.validation import write_security_validation_artifacts


DIST_DIR = REPO_ROOT / 'dist'
ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'fs_p05_empirical_review'
VALIDATION_ROOT = Path(tempfile.gettempdir()) / 'calamum_vulcan_fs_p05_empirical_review'
FIXED_CAPTURED_AT_UTC = '2026-04-18T23:45:00Z'

GUI_REVIEW_SCENARIOS = (
  {
    'name': 'ready',
    'scenario': 'ready',
    'transport_source': 'state-fixture',
    'package_fixture': 'scenario-default',
    'adapter_fixture': 'scenario-default',
  },
  {
    'name': 'blocked',
    'scenario': 'blocked',
    'transport_source': 'state-fixture',
    'package_fixture': 'scenario-default',
    'adapter_fixture': 'scenario-default',
  },
  {
    'name': 'failure',
    'scenario': 'failure',
    'transport_source': 'heimdall-adapter',
    'package_fixture': 'scenario-default',
    'adapter_fixture': 'scenario-default',
  },
)


def _project_version() -> str:
  """Return the current repository package version."""

  with (REPO_ROOT / 'pyproject.toml').open('rb') as handle:
    project = tomllib.load(handle)['project']
  return str(project['version'])


CURRENT_PACKAGE_VERSION = _project_version()

PUBLIC_SUPPORT_POSTURE = {
  'windows': 'empirically reviewed in packaged form for {version}'.format(
    version=CURRENT_PACKAGE_VERSION,
  ),
  'linux': 'scripted-simulation target only for {version}; empirical closeout still pending'.format(
    version=CURRENT_PACKAGE_VERSION,
  ),
  'macos': 'deferred and not part of the {version} published support boundary'.format(
    version=CURRENT_PACKAGE_VERSION,
  ),
  'core_flash_workflow': 'simulation-validated for the {version} package boundary'.format(
    version=CURRENT_PACKAGE_VERSION,
  ),
  'live_companion_controls': 'bounded lab review only for device detection and reboot handoffs',
  'live_firmware_flashing': 'not part of the published {version} support boundary'.format(
    version=CURRENT_PACKAGE_VERSION,
  ),
}


def _print(lines: Sequence[str]) -> None:
  for line in lines:
    print(line)


def _run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
  result = subprocess.run(
    command,
    cwd=cwd,
    capture_output=True,
    env=None,
    text=True,
  )
  if result.returncode != 0:
    if result.stdout:
      print(result.stdout)
    if result.stderr:
      print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode)
  return result


def _run_with_env(
  command: Sequence[str],
  cwd: Path,
  env: Optional[Mapping[str, str]],
) -> subprocess.CompletedProcess[str]:
  result = subprocess.run(
    command,
    cwd=cwd,
    capture_output=True,
    env=env,
    text=True,
  )
  if result.returncode != 0:
    if result.stdout:
      print(result.stdout)
    if result.stderr:
      print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode)
  return result


def _sanitized_qt_env() -> Mapping[str, str]:
  env = dict(os.environ)
  env.pop('QT_QPA_PLATFORM', None)
  env.pop('QT_QPA_FONTDIR', None)
  if sys.platform.startswith('win'):
    env['QT_QPA_PLATFORM'] = 'windows'
  return env


def _find_single_wheel() -> Path:
  wheels = sorted(DIST_DIR.glob('*.whl'))
  if len(wheels) != 1:
    raise SystemExit(
      'Expected exactly one wheel in dist/, found {count}. Run '
      '`python scripts/build_release_artifacts.py` first.'.format(
        count=len(wheels),
      )
    )
  return wheels[0]


@contextmanager
def _installed_import_context(installed_root: Path) -> Iterator[None]:
  original_sys_path = list(sys.path)
  original_modules = {
    name: module
    for name, module in sys.modules.items()
    if name == 'calamum_vulcan' or name.startswith('calamum_vulcan.')
  }
  for name in list(original_modules):
    sys.modules.pop(name, None)
  sys.path.insert(0, str(installed_root))
  try:
    yield
  finally:
    for name in list(sys.modules):
      if name == 'calamum_vulcan' or name.startswith('calamum_vulcan.'):
        sys.modules.pop(name, None)
    sys.modules.update(original_modules)
    sys.path[:] = original_sys_path


def _run_cli_mode(installed_root: Path, cli_args: Sequence[str]) -> int:
  with _installed_import_context(installed_root):
    from calamum_vulcan.app.__main__ import main as app_main

    normalized_args = list(cli_args)
    if normalized_args[:1] == ['--']:
      normalized_args = normalized_args[1:]
    return app_main(normalized_args)


def _capture_gui_mode(
  installed_root: Path,
  scenario: str,
  screenshot_output: Path,
  summary_output: Path,
  transport_source: str,
  package_fixture: str,
  adapter_fixture: str,
  captured_at_utc: str,
) -> int:
  os.environ.pop('QT_QPA_FONTDIR', None)
  if sys.platform.startswith('win'):
    os.environ['QT_QPA_PLATFORM'] = 'windows'
  else:
    os.environ.pop('QT_QPA_PLATFORM', None)

  with _installed_import_context(installed_root):
    from calamum_vulcan.app.demo import build_demo_adapter_session
    from calamum_vulcan.app.demo import build_demo_package_assessment
    from calamum_vulcan.app.demo import build_demo_session
    from calamum_vulcan.app.demo import scenario_label
    from calamum_vulcan.app.qt_shell import ShellWindow
    from calamum_vulcan.app.qt_shell import get_or_create_application
    from calamum_vulcan.app.qt_compat import QtCore
    from calamum_vulcan.domain.reporting import build_session_evidence_report
    from calamum_vulcan.app.view_models import build_shell_view_model

    if transport_source == 'heimdall-adapter':
      session, package_assessment, transport_trace = build_demo_adapter_session(
        scenario,
        package_fixture_name=package_fixture,
        adapter_fixture_name=adapter_fixture,
      )
    else:
      session = build_demo_session(scenario)
      transport_trace = None
      package_assessment = None
      if session.guards.package_loaded or package_fixture != 'scenario-default':
        package_assessment = build_demo_package_assessment(
          scenario,
          session=session,
          package_fixture_name=package_fixture,
        )

    report = build_session_evidence_report(
      session,
      scenario_name=scenario_label(scenario),
      package_assessment=package_assessment,
      transport_trace=transport_trace,
      captured_at_utc=captured_at_utc,
    )
    model = build_shell_view_model(
      session,
      scenario_name=scenario_label(scenario),
      package_assessment=package_assessment,
      transport_trace=transport_trace,
      session_report=report,
    )

    screenshot_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)

    application = get_or_create_application()
    window = ShellWindow(model)
    window.resize(1680, 1040)
    capture_result = {'saved': False}

    def _capture() -> None:
      application.processEvents()
      capture_result['saved'] = window.grab().save(str(screenshot_output))
      summary_output.write_text(
        json.dumps(
          {
            'scenario': scenario,
            'window_title': window.windowTitle(),
            'size': {
              'width': window.width(),
              'height': window.height(),
              'minimum_width': window.minimumWidth(),
              'minimum_height': window.minimumHeight(),
            },
            'panel_titles': window.panel_titles(),
            'action_labels': window.action_labels(),
            'live_status': window.live_status_text(),
            'phase_label': model.phase_label,
            'gate_label': model.gate_label,
          },
          indent=2,
          sort_keys=True,
        ),
        encoding='utf-8',
      )
      window.close()
      application.quit()

    QtCore.QTimer.singleShot(350, _capture)
    window.show()
    exit_code = application.exec()
    if exit_code != 0:
      return exit_code
    if not capture_result['saved']:
      raise SystemExit('Failed to save screenshot for scenario: {scenario}'.format(
        scenario=scenario,
      ))
    return 0


def _write_text(path: Path, content: str) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding='utf-8')


def _run_cli_probe(
  script_path: Path,
  installed_root: Path,
  workdir: Path,
  cli_args: Sequence[str],
) -> subprocess.CompletedProcess[str]:
  return _run(
    [
      sys.executable,
      str(script_path),
      'cli',
      '--installed-root',
      str(installed_root),
      '--',
      *cli_args,
    ],
    cwd=workdir,
  )


def _run_capture_probe(
  script_path: Path,
  installed_root: Path,
  workdir: Path,
  scenario_name: str,
  screenshot_output: Path,
  summary_output: Path,
  transport_source: str,
  package_fixture: str,
  adapter_fixture: str,
) -> None:
  _run_with_env(
    [
      sys.executable,
      str(script_path),
      'capture',
      '--installed-root',
      str(installed_root),
      '--scenario',
      scenario_name,
      '--screenshot-output',
      str(screenshot_output),
      '--summary-output',
      str(summary_output),
      '--transport-source',
      transport_source,
      '--package-fixture',
      package_fixture,
      '--adapter-fixture',
      adapter_fixture,
      '--captured-at-utc',
      FIXED_CAPTURED_AT_UTC,
    ],
    cwd=workdir,
    env=_sanitized_qt_env(),
  )


def _assert_contains(text: str, expected: str, error_message: str) -> None:
  if expected not in text:
    raise SystemExit(error_message)


def _read_json(path: Path) -> object:
  return json.loads(path.read_text(encoding='utf-8'))


def _write_summary_markdown(
  path: Path,
  wheel_path: Path,
  install_root: Path,
  screenshot_paths: Mapping[str, Path],
) -> None:
  lines = [
    '## FS-P05 empirical review summary',
    '',
    '- wheel: `{wheel}`'.format(wheel=wheel_path.name),
    '- install root: `{root}`'.format(root=install_root),
    '- quickstart: installed help, ready describe-only, and sprint-close bundle all passed',
    '- evidence review: blocked and failure Markdown exports remained readable and recovery-oriented',
    '- GUI review: screenshots captured for ready, blocked, and failure packaged scenarios',
    '',
    '### Support posture pinned for `{version}`'.format(
      version=CURRENT_PACKAGE_VERSION,
    ),
    '',
  ]
  for label, value in PUBLIC_SUPPORT_POSTURE.items():
    lines.append('- `{label}`: {value}'.format(label=label, value=value))
  lines.extend(['', '### Screenshot artifacts', ''])
  for name, screenshot_path in screenshot_paths.items():
    lines.append('- `{name}`: `{path}`'.format(name=name, path=screenshot_path))
  _write_text(path, '\n'.join(lines) + '\n')


def _run_empirical_review() -> int:
  wheel_path = _find_single_wheel()
  script_path = Path(__file__).resolve()

  if ARCHIVE_ROOT.exists():
    shutil.rmtree(ARCHIVE_ROOT)
  ARCHIVE_ROOT.mkdir(parents=True)

  if VALIDATION_ROOT.exists():
    shutil.rmtree(VALIDATION_ROOT)
  VALIDATION_ROOT.mkdir(parents=True)

  install_root = VALIDATION_ROOT / 'install_root'
  workdir = VALIDATION_ROOT / 'workdir'
  install_root.mkdir()
  workdir.mkdir()

  _run(
    [
      sys.executable,
      '-m',
      'pip',
      'install',
      '--no-deps',
      '--target',
      str(install_root),
      str(wheel_path),
    ],
    cwd=REPO_ROOT,
  )

  help_result = _run_cli_probe(script_path, install_root, workdir, ['--help'])
  _assert_contains(
    help_result.stdout,
    '--integration-suite',
    'Installed help output lost the integration-suite flag.',
  )
  _write_text(ARCHIVE_ROOT / 'quickstart_help.txt', help_result.stdout)

  ready_result = _run_cli_probe(
    script_path,
    install_root,
    workdir,
    ['--scenario', 'ready', '--describe-only'],
  )
  _assert_contains(
    ready_result.stdout,
    'phase="Ready to Execute" gate="Gate Ready"',
    'Installed ready quickstart did not preserve the expected shell summary.',
  )
  _write_text(ARCHIVE_ROOT / 'quickstart_ready.txt', ready_result.stdout)

  sprint_close_path = ARCHIVE_ROOT / 'sprint_close_bundle.md'
  _run_cli_probe(
    script_path,
    install_root,
    workdir,
    [
      '--integration-suite',
      'sprint-close',
      '--suite-format',
      'markdown',
      '--suite-output',
      str(sprint_close_path),
      '--captured-at-utc',
      FIXED_CAPTURED_AT_UTC,
    ],
  )
  sprint_close_markdown = sprint_close_path.read_text(encoding='utf-8')
  _assert_contains(
    sprint_close_markdown,
    'Calamum Vulcan FS-08 sprint-close bundle',
    'Installed sprint-close bundle lost the expected heading.',
  )

  blocked_evidence_path = ARCHIVE_ROOT / 'evidence' / 'blocked_review.md'
  _run_cli_probe(
    script_path,
    install_root,
    workdir,
    [
      '--scenario',
      'blocked',
      '--describe-only',
      '--export-evidence',
      '--evidence-format',
      'markdown',
      '--evidence-output',
      str(blocked_evidence_path),
      '--captured-at-utc',
      FIXED_CAPTURED_AT_UTC,
    ],
  )
  blocked_markdown = blocked_evidence_path.read_text(encoding='utf-8')
  _assert_contains(
    blocked_markdown,
    '### Recovery guidance',
    'Blocked evidence export is missing the recovery guidance section.',
  )

  failure_evidence_path = ARCHIVE_ROOT / 'evidence' / 'failure_review.md'
  _run_cli_probe(
    script_path,
    install_root,
    workdir,
    [
      '--scenario',
      'failure',
      '--transport-source',
      'heimdall-adapter',
      '--describe-only',
      '--export-evidence',
      '--evidence-format',
      'markdown',
      '--evidence-output',
      str(failure_evidence_path),
      '--captured-at-utc',
      FIXED_CAPTURED_AT_UTC,
    ],
  )
  failure_markdown = failure_evidence_path.read_text(encoding='utf-8')
  _assert_contains(
    failure_markdown,
    'Stabilize the direct USB path',
    'Failure evidence export lost the expected recovery wording.',
  )
  _assert_contains(
    failure_markdown,
    'USB transfer timeout during partition write',
    'Failure evidence export lost the normalized failure reason.',
  )

  screenshot_paths = {}
  screenshot_summary_paths = {}
  for scenario in GUI_REVIEW_SCENARIOS:
    screenshot_path = ARCHIVE_ROOT / 'screenshots' / '{name}.png'.format(
      name=scenario['name'],
    )
    summary_path = ARCHIVE_ROOT / 'screenshots' / '{name}.json'.format(
      name=scenario['name'],
    )
    _run_capture_probe(
      script_path,
      install_root,
      workdir,
      scenario['scenario'],
      screenshot_path,
      summary_path,
      scenario['transport_source'],
      scenario['package_fixture'],
      scenario['adapter_fixture'],
    )
    screenshot_paths[scenario['name']] = screenshot_path
    screenshot_summary_paths[scenario['name']] = summary_path

  review_summary = {
    'wheel': wheel_path.name,
    'archive_root': str(ARCHIVE_ROOT),
    'validation_root': str(VALIDATION_ROOT),
    'quickstart': {
      'help': 'passed',
      'ready_describe': 'passed',
      'sprint_close_bundle': 'passed',
    },
    'evidence_review': {
      'blocked_markdown': 'passed',
      'failure_markdown': 'passed',
    },
    'screenshots': {
      name: {
        'image_path': str(screenshot_paths[name]),
        'summary_path': str(screenshot_summary_paths[name]),
      }
      for name in screenshot_paths
    },
    'support_posture': PUBLIC_SUPPORT_POSTURE,
  }
  _write_text(
    ARCHIVE_ROOT / 'empirical_review_summary.json',
    json.dumps(review_summary, indent=2, sort_keys=True) + '\n',
  )
  security_summary = run_security_validation_suite(REPO_ROOT)
  write_security_validation_artifacts(ARCHIVE_ROOT / 'security_validation', security_summary)
  if security_summary.decision == 'failed':
    raise SystemExit('Security validation failed for the FS-P05 empirical review closure.')
  _write_summary_markdown(
    ARCHIVE_ROOT / 'empirical_review_summary.md',
    wheel_path,
    install_root,
    screenshot_paths,
  )

  _print(
    [
      'archive_root="{root}"'.format(root=ARCHIVE_ROOT),
      'wheel="{wheel}"'.format(wheel=wheel_path.name),
      'security_validation="{decision}"'.format(
        decision=security_summary.decision,
      ),
      'clean_install="passed"',
      'quickstart_walkthrough="passed"',
      'visible_gui_review="passed"',
      'evidence_readability="passed"',
      'support_posture="pinned"',
      'empirical_review_contract="passed"',
    ]
  )
  return 0


def _build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description='Run the FS-P05 empirical review and public-doc readiness stack.',
  )
  subparsers = parser.add_subparsers(dest='mode')

  cli_parser = subparsers.add_parser('cli')
  cli_parser.add_argument('--installed-root', required=True)
  cli_parser.add_argument('cli_args', nargs=argparse.REMAINDER)

  capture_parser = subparsers.add_parser('capture')
  capture_parser.add_argument('--installed-root', required=True)
  capture_parser.add_argument('--scenario', required=True)
  capture_parser.add_argument('--screenshot-output', required=True)
  capture_parser.add_argument('--summary-output', required=True)
  capture_parser.add_argument('--transport-source', default='state-fixture')
  capture_parser.add_argument('--package-fixture', default='scenario-default')
  capture_parser.add_argument('--adapter-fixture', default='scenario-default')
  capture_parser.add_argument('--captured-at-utc', default=FIXED_CAPTURED_AT_UTC)

  return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
  parser = _build_parser()
  args = parser.parse_args(argv)

  if args.mode == 'cli':
    return _run_cli_mode(Path(args.installed_root), args.cli_args)
  if args.mode == 'capture':
    return _capture_gui_mode(
      Path(args.installed_root),
      args.scenario,
      Path(args.screenshot_output),
      Path(args.summary_output),
      args.transport_source,
      args.package_fixture,
      args.adapter_fixture,
      args.captured_at_utc,
    )
  return _run_empirical_review()


if __name__ == '__main__':
  raise SystemExit(main())
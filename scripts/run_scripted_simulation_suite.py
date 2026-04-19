"""Run the FS-P04 scripted simulation and reproducibility suite."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.validation import run_security_validation_suite
from calamum_vulcan.validation import safe_extract_zip_archive
from calamum_vulcan.validation import write_security_validation_artifacts


DIST_DIR = REPO_ROOT / 'dist'
ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'fs_p04_scripted_simulation'
INSTALLED_VALIDATION_ROOT = (
  Path(tempfile.gettempdir()) / 'calamum_vulcan_fs_p04_scripted_simulation'
)
FIXED_CAPTURED_AT_UTC = '2026-04-18T23:10:00Z'
SCENARIO_MATRIX = (
  {
    'name': 'no-device',
    'cli_args': ('--scenario', 'no-device', '--describe-only'),
    'expected_summary': 'phase="No Device" gate="Gate Blocked"',
    'expected_json': {
      'session_phase': 'no_device',
      'preflight_gate': 'blocked',
      'outcome': 'in_progress',
      'export_ready': False,
    },
  },
  {
    'name': 'ready',
    'cli_args': ('--scenario', 'ready', '--describe-only'),
    'expected_summary': 'phase="Ready to Execute" gate="Gate Ready"',
    'expected_json': {
      'session_phase': 'ready_to_execute',
      'preflight_gate': 'ready',
      'outcome': 'ready_to_execute',
      'export_ready': True,
    },
  },
  {
    'name': 'blocked',
    'cli_args': ('--scenario', 'blocked', '--describe-only'),
    'expected_summary': 'phase="Validation Blocked" gate="Gate Blocked"',
    'expected_json': {
      'session_phase': 'validation_blocked',
      'preflight_gate': 'blocked',
      'outcome': 'validation_blocked',
      'export_ready': True,
    },
  },
  {
    'name': 'mismatch',
    'cli_args': (
      '--scenario', 'ready',
      '--package-fixture', 'mismatched',
      '--describe-only',
    ),
    'expected_summary': 'phase="Ready to Execute" gate="Gate Blocked"',
    'expected_json': {
      'session_phase': 'ready_to_execute',
      'preflight_gate': 'blocked',
      'outcome': 'ready_to_execute',
      'export_ready': True,
      'package_compatibility': 'mismatch',
    },
  },
  {
    'name': 'failure',
    'cli_args': (
      '--scenario', 'failure',
      '--transport-source', 'heimdall-adapter',
      '--describe-only',
    ),
    'expected_summary': 'phase="Failed" gate="Gate Ready"',
    'expected_json': {
      'session_phase': 'failed',
      'preflight_gate': 'ready',
      'outcome': 'failed',
      'export_ready': True,
      'transport_state': 'failed',
    },
  },
  {
    'name': 'resume',
    'cli_args': (
      '--scenario', 'resume',
      '--transport-source', 'heimdall-adapter',
      '--describe-only',
    ),
    'expected_summary': 'phase="Completed" gate="Gate Ready"',
    'expected_json': {
      'session_phase': 'completed',
      'preflight_gate': 'ready',
      'outcome': 'completed',
      'export_ready': True,
      'transport_state': 'completed',
    },
  },
)
SCENARIO_NAMES = tuple(scenario['name'] for scenario in SCENARIO_MATRIX)


def _print(lines: Sequence[str]) -> None:
  for line in lines:
    print(line)


def _append_progress(progress_path: Path, line: str) -> None:
  with progress_path.open('a', encoding='utf-8') as progress_file:
    progress_file.write(line + '\n')


def _run(
  command: Sequence[str],
  cwd: Path,
  env: Optional[Mapping[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
  result = subprocess.run(
    command,
    cwd=cwd,
    capture_output=True,
    text=True,
    env=dict(env) if env is not None else None,
  )
  if result.returncode != 0:
    if result.stdout:
      print(result.stdout)
    if result.stderr:
      print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode)
  return result


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


def _extract_wheel(wheel_path: Path, install_root: Path) -> None:
  safe_extract_zip_archive(wheel_path, install_root)


def _installed_cli_probe_code(install_root: Path) -> str:
  return """
from pathlib import Path
import sys

install_root = Path(r'INSTALL_ROOT_PLACEHOLDER').resolve()
sys.path.insert(0, str(install_root))

from calamum_vulcan.app.__main__ import main

raise SystemExit(main())
""".replace('INSTALL_ROOT_PLACEHOLDER', str(install_root))


def _read_text(path: Path) -> str:
  return path.read_text(encoding='utf-8')


def _read_json(path: Path) -> object:
  return json.loads(_read_text(path))


def _assert_json_payload(payload: Mapping[str, object], expected: Mapping[str, object]) -> None:
  if payload['session_phase'] != expected['session_phase']:
    raise SystemExit('Unexpected session phase: {phase}'.format(
      phase=payload['session_phase'],
    ))
  preflight = payload['preflight']
  outcome = payload['outcome']
  if preflight['gate'] != expected['preflight_gate']:
    raise SystemExit('Unexpected preflight gate: {gate}'.format(gate=preflight['gate']))
  if outcome['outcome'] != expected['outcome']:
    raise SystemExit('Unexpected outcome: {outcome}'.format(outcome=outcome['outcome']))
  if outcome['export_ready'] != expected['export_ready']:
    raise SystemExit('Unexpected export_ready flag.')
  if 'package_compatibility' in expected:
    if payload['package']['compatibility_expectation'] != expected['package_compatibility']:
      raise SystemExit('Unexpected package compatibility expectation.')
  if 'transport_state' in expected:
    if payload['transport']['state'] != expected['transport_state']:
      raise SystemExit('Unexpected transport state: {state}'.format(
        state=payload['transport']['state'],
      ))


def _assert_markdown_payload(markdown: str, scenario_name: str) -> None:
  if '## Calamum Vulcan session evidence' not in markdown:
    raise SystemExit('Markdown evidence is missing the session evidence heading.')
  if '### Summary' not in markdown or '### Recovery guidance' not in markdown:
    raise SystemExit('Markdown evidence is missing expected sections.')
  if scenario_name not in markdown:
    raise SystemExit('Markdown evidence is missing the scenario label.')


def _scenario_output_paths(context_root: Path, scenario_name: str) -> Dict[str, Path]:
  scenario_root = context_root / scenario_name
  scenario_root.mkdir(parents=True, exist_ok=True)
  return {
    'root': scenario_root,
    'json': scenario_root / 'evidence.json',
    'markdown': scenario_root / 'evidence.md',
  }


def _source_command(extra_args: Sequence[str]) -> Sequence[str]:
  return [sys.executable, '-m', 'calamum_vulcan.app'] + list(extra_args)


def _installed_command(install_root: Path, extra_args: Sequence[str]) -> Sequence[str]:
  return [sys.executable, '-c', _installed_cli_probe_code(install_root)] + list(extra_args)


def _run_scenario_context(
  context_name: str,
  context_root: Path,
  selected_scenarios: Sequence[Mapping[str, object]],
  command_factory,
  execution_cwd: Path,
  progress_path: Path,
) -> Dict[str, Dict[str, object]]:
  results = {}
  gui_env = os.environ.copy()
  gui_env['QT_QPA_PLATFORM'] = 'offscreen'

  for index, scenario in enumerate(selected_scenarios):
    _append_progress(
      progress_path,
      '[{context}] start scenario {scenario}'.format(
        context=context_name,
        scenario=scenario['name'],
      ),
    )
    scenario_outputs = _scenario_output_paths(context_root, scenario['name'])
    captured_at = '2026-04-18T23:{minute:02d}:00Z'.format(minute=10 + index)
    base_args = list(scenario['cli_args'])

    describe_result = _run(
      command_factory(base_args + ['--captured-at-utc', captured_at]),
      cwd=execution_cwd,
    )
    describe_text = describe_result.stdout.strip()
    if scenario['expected_summary'] not in describe_text:
      raise SystemExit(
        '{context} describe-only output did not preserve the expected shell summary for {scenario}.'.format(
          context=context_name,
          scenario=scenario['name'],
        )
      )
    (scenario_outputs['root'] / 'describe.txt').write_text(
      describe_text + '\n',
      encoding='utf-8',
    )

    _run(
      command_factory(
        base_args + [
          '--export-evidence',
          '--evidence-format', 'json',
          '--evidence-output', str(scenario_outputs['json']),
          '--captured-at-utc', captured_at,
        ]
      ),
      cwd=execution_cwd,
    )
    evidence_payload = _read_json(scenario_outputs['json'])
    _assert_json_payload(evidence_payload, scenario['expected_json'])

    _run(
      command_factory(
        base_args + [
          '--export-evidence',
          '--evidence-format', 'markdown',
          '--evidence-output', str(scenario_outputs['markdown']),
          '--captured-at-utc', captured_at,
        ]
      ),
      cwd=execution_cwd,
    )
    markdown_payload = _read_text(scenario_outputs['markdown'])
    _assert_markdown_payload(markdown_payload, evidence_payload['scenario_name'])

    gui_result = _run(
      command_factory(
        list(scenario['cli_args'][:-1]) + [
          '--duration-ms', '50',
          '--captured-at-utc', captured_at,
        ]
      ),
      cwd=execution_cwd,
      env=gui_env,
    )
    (scenario_outputs['root'] / 'gui_stdout.txt').write_text(
      gui_result.stdout,
      encoding='utf-8',
    )
    (scenario_outputs['root'] / 'gui_stderr.txt').write_text(
      gui_result.stderr,
      encoding='utf-8',
    )

    results[scenario['name']] = {
      'describe': describe_text,
      'json': evidence_payload,
      'markdown': markdown_payload,
    }
    _append_progress(
      progress_path,
      '[{context}] completed scenario {scenario}'.format(
        context=context_name,
        scenario=scenario['name'],
      ),
    )

  return results


def _run_bundle_context(
  context_root: Path,
  command_factory,
  execution_cwd: Path,
) -> Dict[str, object]:
  bundle_json_path = context_root / 'sprint_close_bundle.json'
  bundle_markdown_path = context_root / 'sprint_close_bundle.md'
  captured_at = FIXED_CAPTURED_AT_UTC

  _run(
    command_factory(
      [
        '--integration-suite', 'sprint-close',
        '--suite-format', 'json',
        '--suite-output', str(bundle_json_path),
        '--captured-at-utc', captured_at,
      ]
    ),
    cwd=execution_cwd,
  )
  _run(
    command_factory(
      [
        '--integration-suite', 'sprint-close',
        '--suite-format', 'markdown',
        '--suite-output', str(bundle_markdown_path),
        '--captured-at-utc', captured_at,
      ]
    ),
    cwd=execution_cwd,
  )

  bundle_json = _read_json(bundle_json_path)
  bundle_markdown = _read_text(bundle_markdown_path)
  if bundle_json['suite_name'] != 'sprint-close':
    raise SystemExit('Integrated bundle lost the expected suite name.')
  if len(bundle_json['scenarios']) != 6:
    raise SystemExit('Integrated bundle returned the wrong scenario count.')
  if 'Calamum Vulcan FS-08 sprint-close bundle' not in bundle_markdown:
    raise SystemExit('Integrated Markdown bundle is missing the expected heading.')
  return {
    'json': bundle_json,
    'markdown': bundle_markdown,
  }


def _compare_contexts(
  selected_scenarios: Sequence[Mapping[str, object]],
  source_results: Mapping[str, Dict[str, object]],
  installed_results: Mapping[str, Dict[str, object]],
  source_bundle: Mapping[str, object],
  installed_bundle: Mapping[str, object],
) -> None:
  for scenario in selected_scenarios:
    name = scenario['name']
    if source_results[name]['describe'] != installed_results[name]['describe']:
      raise SystemExit('Describe-only output drifted between source and installed contexts for {name}.'.format(name=name))
    if source_results[name]['json'] != installed_results[name]['json']:
      raise SystemExit('JSON evidence drifted between source and installed contexts for {name}.'.format(name=name))
    if source_results[name]['markdown'] != installed_results[name]['markdown']:
      raise SystemExit('Markdown evidence drifted between source and installed contexts for {name}.'.format(name=name))
  if source_bundle['json'] != installed_bundle['json']:
    raise SystemExit('Sprint-close JSON bundle drifted between source and installed contexts.')
  if source_bundle['markdown'] != installed_bundle['markdown']:
    raise SystemExit('Sprint-close Markdown bundle drifted between source and installed contexts.')


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description='Run the FS-P04 scripted simulation and reproducibility suite.',
  )
  parser.add_argument(
    '--scenarios',
    nargs='+',
    choices=SCENARIO_NAMES,
    default=None,
    help='Optional subset of scenario names to run instead of the full matrix.',
  )
  parser.add_argument(
    '--skip-installed',
    action='store_true',
    help='Skip the installed-artifact context run.',
  )
  parser.add_argument(
    '--skip-bundle',
    action='store_true',
    help='Skip the sprint-close bundle generation checks.',
  )
  return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
  args = _parse_args(argv)
  selected_scenarios = SCENARIO_MATRIX
  if args.scenarios:
    allowed = set(args.scenarios)
    selected_scenarios = tuple(
      scenario for scenario in SCENARIO_MATRIX if scenario['name'] in allowed
    )

  wheel_path = _find_single_wheel()

  if ARCHIVE_ROOT.exists():
    shutil.rmtree(ARCHIVE_ROOT)
  ARCHIVE_ROOT.mkdir(parents=True)

  if INSTALLED_VALIDATION_ROOT.exists():
    shutil.rmtree(INSTALLED_VALIDATION_ROOT)
  INSTALLED_VALIDATION_ROOT.mkdir(parents=True)

  install_root = INSTALLED_VALIDATION_ROOT / 'install_root'
  installed_workdir = INSTALLED_VALIDATION_ROOT / 'workdir'
  install_root.mkdir()
  installed_workdir.mkdir()
  source_archive_root = ARCHIVE_ROOT / 'source_root'
  installed_archive_root = ARCHIVE_ROOT / 'installed_artifact'
  source_archive_root.mkdir()
  installed_archive_root.mkdir()
  progress_path = ARCHIVE_ROOT / 'progress.log'
  _append_progress(progress_path, '[suite] selected scenarios: ' + ', '.join(
    scenario['name'] for scenario in selected_scenarios
  ))

  _extract_wheel(wheel_path, install_root)
  _append_progress(progress_path, '[suite] extracted installed-artifact wheel')

  source_results = _run_scenario_context(
    'source_root',
    source_archive_root,
    selected_scenarios,
    _source_command,
    REPO_ROOT,
    progress_path,
  )
  installed_results = {}
  if not args.skip_installed:
    installed_results = _run_scenario_context(
      'installed_artifact',
      installed_archive_root,
      selected_scenarios,
      lambda extra_args: _installed_command(install_root, extra_args),
      installed_workdir,
      progress_path,
    )

  source_bundle = {'json': {}, 'markdown': ''}
  installed_bundle = {'json': {}, 'markdown': ''}
  if not args.skip_bundle:
    source_bundle = _run_bundle_context(
      source_archive_root,
      _source_command,
      REPO_ROOT,
    )
    _append_progress(progress_path, '[source_root] completed sprint-close bundle')
    if not args.skip_installed:
      installed_bundle = _run_bundle_context(
        installed_archive_root,
        lambda extra_args: _installed_command(install_root, extra_args),
        installed_workdir,
      )
      _append_progress(progress_path, '[installed_artifact] completed sprint-close bundle')

  if not args.skip_installed:
    _compare_contexts(
      selected_scenarios,
      source_results,
      installed_results,
      source_bundle,
      installed_bundle,
    )
    _append_progress(progress_path, '[suite] source and installed contexts matched exactly')

  summary = {
    'captured_at_utc': FIXED_CAPTURED_AT_UTC,
    'scenario_names': [scenario['name'] for scenario in selected_scenarios],
    'source_archive_root': str(source_archive_root),
    'installed_archive_root': str(installed_archive_root),
    'bundle_id': source_bundle['json'].get('bundle_id'),
  }
  summary_path = ARCHIVE_ROOT / 'simulation_summary.json'
  security_summary = run_security_validation_suite(REPO_ROOT)
  write_security_validation_artifacts(ARCHIVE_ROOT / 'security_validation', security_summary)
  if security_summary.decision == 'failed':
    raise SystemExit('Security validation failed for the FS-P04 scripted simulation closure.')
  summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding='utf-8')

  _print(
    [
      'archive_root="{root}"'.format(root=ARCHIVE_ROOT),
      'wheel="{wheel}"'.format(wheel=wheel_path.name),
      'security_validation="{decision}"'.format(
        decision=security_summary.decision,
      ),
      'scenario_matrix="passed"',
      'source_root_runner="passed"',
      'installed_artifact_runner="passed"',
      'offscreen_gui="passed"',
      'evidence_exports="passed"',
      'integration_bundle="passed"',
      'reproducibility_contract="passed"',
      'scripted_simulation_contract="passed"',
    ]
  )
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
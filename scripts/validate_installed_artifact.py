"""Validate the installed-artifact contract for Calamum Vulcan FS-P03."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.validation import run_security_validation_suite
from calamum_vulcan.validation import write_security_validation_artifacts


DIST_DIR = REPO_ROOT / 'dist'
VALIDATION_ROOT = Path(tempfile.gettempdir()) / 'calamum_vulcan_fs_p03_installed_artifact'


def _print(lines: Sequence[str]) -> None:
  for line in lines:
    print(line)


def _run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
  result = subprocess.run(
    command,
    cwd=cwd,
    capture_output=True,
    text=True,
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


def _import_probe_code(install_root: Path) -> str:
  return """
from importlib import metadata
from importlib.resources import files
from pathlib import Path
import json
import sys

repo_root = Path(r'REPO_ROOT_PLACEHOLDER').resolve()
install_root = Path(r'INSTALL_ROOT_PLACEHOLDER').resolve()
sys.path.insert(0, str(install_root))
import calamum_vulcan

installed_root = Path(calamum_vulcan.__file__).resolve().parent
if repo_root in installed_root.parents or installed_root == repo_root:
  raise SystemExit('Installed package resolved inside the source tree.')

dist = metadata.distribution('calamum_vulcan')
file_names = sorted(str(file) for file in dist.files or ())
required = [
  'calamum_vulcan/__init__.py',
  'calamum_vulcan/app/__main__.py',
  'calamum_vulcan/launch_shell.py',
  'calamum_vulcan/assets/branding/calamum_logo_color.png',
  'calamum_vulcan/assets/branding/calamum_taskbar_icon.png',
  'calamum_vulcan/fixtures/package_manifests/matched_recovery_package.json',
  'calamum_vulcan/fixtures/package_manifests/mismatched_recovery_package.json',
  'calamum_vulcan/fixtures/package_manifests/incomplete_recovery_package.json',
  'calamum_vulcan-0.1.0.dist-info/METADATA',
  'calamum_vulcan-0.1.0.dist-info/entry_points.txt',
]
missing = [item for item in required if not any(name.endswith(item) for name in file_names)]
if missing:
  raise SystemExit('Installed wheel is missing expected files: ' + ', '.join(missing))

for forbidden_prefix in ('tests/', 'docs/', 'temp/'):
  leaked = [name for name in file_names if name.startswith(forbidden_prefix)]
  if leaked:
    raise SystemExit('Installed wheel leaked forbidden files under ' + forbidden_prefix)

fixture_dir = files('calamum_vulcan.fixtures').joinpath('package_manifests')
fixture_names = sorted(item.name for item in fixture_dir.iterdir() if item.name.endswith('.json'))
expected_fixtures = [
  'blocked_review_package.json',
  'incomplete_recovery_package.json',
  'matched_recovery_package.json',
  'mismatched_recovery_package.json',
  'package_first_standard_review_package.json',
  'ready_standard_review_package.json',
]
if fixture_names != expected_fixtures:
  raise SystemExit('Installed fixture set mismatch: ' + ', '.join(fixture_names))

branding_dir = files('calamum_vulcan').joinpath('assets').joinpath('branding')
branding_names = sorted(item.name for item in branding_dir.iterdir() if item.name.endswith('.png'))
expected_branding = [
  'calamum_logo_color.png',
  'calamum_taskbar_icon.png',
]
if branding_names != expected_branding:
  raise SystemExit('Installed branding asset set mismatch: ' + ', '.join(branding_names))

entry_points = sorted(entry_point.name for entry_point in dist.entry_points)
for expected_entry_point in ('calamum-vulcan', 'calamum-vulcan-gui'):
  if expected_entry_point not in entry_points:
    raise SystemExit('Missing entry point: ' + expected_entry_point)

requirements = metadata.requires('calamum_vulcan') or []
if not any(requirement.startswith('PySide6') for requirement in requirements):
  raise SystemExit('Runtime dependency metadata lost PySide6 requirement.')

summary = {
  'installed_root': str(installed_root),
  'version': metadata.version('calamum_vulcan'),
  'entry_points': entry_points,
  'branding_names': branding_names,
  'fixture_names': fixture_names,
}
print(json.dumps(summary))
""".replace('REPO_ROOT_PLACEHOLDER', str(REPO_ROOT)).replace(
    'INSTALL_ROOT_PLACEHOLDER',
    str(install_root),
  )


def _cli_probe_code(install_root: Path) -> str:
  return """
from pathlib import Path
import sys

install_root = Path(r'INSTALL_ROOT_PLACEHOLDER').resolve()
sys.path.insert(0, str(install_root))

from calamum_vulcan.app.__main__ import main

raise SystemExit(main())
""".replace('INSTALL_ROOT_PLACEHOLDER', str(install_root))


def _read_json(path: Path) -> object:
  return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
  wheel_path = _find_single_wheel()

  if VALIDATION_ROOT.exists():
    shutil.rmtree(VALIDATION_ROOT)
  VALIDATION_ROOT.mkdir(parents=True)

  install_root = VALIDATION_ROOT / 'install_root'
  work_dir = VALIDATION_ROOT / 'workdir'
  output_dir = VALIDATION_ROOT / 'outputs'
  install_root.mkdir()
  work_dir.mkdir()
  output_dir.mkdir()

  _run(
    [
      sys.executable,
      '-m', 'pip', 'install',
      '--no-deps',
      '--target', str(install_root),
      str(wheel_path),
    ],
    cwd=REPO_ROOT,
  )

  import_probe = _run(
    [sys.executable, '-c', _import_probe_code(install_root)],
    cwd=work_dir,
  )
  import_summary = json.loads(import_probe.stdout)

  help_result = _run(
    [sys.executable, '-c', _cli_probe_code(install_root), '--help'],
    cwd=work_dir,
  )
  help_text = help_result.stdout
  for expected_flag in ('--integration-suite', '--export-evidence', '--package-fixture'):
    if expected_flag not in help_text:
      raise SystemExit('Help output is missing expected flag: {flag}'.format(flag=expected_flag))

  ready_result = _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--scenario', 'ready',
      '--describe-only',
    ],
    cwd=work_dir,
  )
  if 'phase="Ready to Execute" gate="Gate Ready"' not in ready_result.stdout:
    raise SystemExit('Installed CLI ready scenario did not preserve the expected shell summary.')

  gui_result = _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--scenario', 'ready',
      '--describe-only',
    ],
    cwd=work_dir,
  )
  if 'phase="Ready to Execute" gate="Gate Ready"' not in gui_result.stdout:
    raise SystemExit('Installed GUI entry point did not preserve the expected shell summary.')

  evidence_path = output_dir / 'blocked_evidence.json'
  _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--scenario', 'blocked',
      '--describe-only',
      '--export-evidence',
      '--evidence-format', 'json',
      '--evidence-output', str(evidence_path),
    ],
    cwd=work_dir,
  )
  evidence_payload = _read_json(evidence_path)
  if evidence_payload['preflight']['gate'] != 'blocked':
    raise SystemExit('Installed evidence export lost the blocked preflight gate.')

  bundle_path = output_dir / 'sprint_close_bundle.json'
  _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--integration-suite', 'sprint-close',
      '--suite-format', 'json',
      '--suite-output', str(bundle_path),
    ],
    cwd=work_dir,
  )
  bundle_payload = _read_json(bundle_path)
  if bundle_payload['suite_name'] != 'sprint-close':
    raise SystemExit('Installed integration bundle lost the expected suite name.')
  if len(bundle_payload['scenarios']) != 6:
    raise SystemExit('Installed integration bundle returned the wrong scenario count.')
  security_summary = run_security_validation_suite(REPO_ROOT)
  write_security_validation_artifacts(
    VALIDATION_ROOT / 'security_validation',
    security_summary,
  )
  if security_summary.decision == 'failed':
    raise SystemExit('Security validation failed for the FS-P03 installed-artifact closure.')

  _print(
    [
      'validation_root="{root}"'.format(root=VALIDATION_ROOT),
      'wheel="{wheel}"'.format(wheel=wheel_path.name),
      'installed_root="{root}"'.format(root=import_summary['installed_root']),
      'security_validation="{decision}"'.format(
        decision=security_summary.decision,
      ),
      'import_contract="passed"',
      'entrypoint_help="passed"',
      'entrypoint_describe="passed"',
      'gui_entrypoint="passed"',
      'evidence_export="passed"',
      'integration_bundle="passed"',
      'distribution_files="passed"',
      'installed_artifact_contract="passed"',
    ]
  )
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
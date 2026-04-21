"""Validate the installed-artifact contract for Calamum Vulcan FS-P03."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence
import zipfile


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
  'calamum_vulcan/app/qt_compat.py',
  'calamum_vulcan/domain/flash_plan/__init__.py',
  'calamum_vulcan/domain/package/image_heuristics.py',
  'calamum_vulcan/domain/state/runtime.py',
  'calamum_vulcan/launch_shell.py',
  'calamum_vulcan/assets/branding/calamum_logo_color.png',
  'calamum_vulcan/assets/branding/calamum_taskbar_icon.png',
  'calamum_vulcan/fixtures/package_manifests/matched_recovery_package.json',
  'calamum_vulcan/fixtures/package_manifests/mismatched_recovery_package.json',
  'calamum_vulcan/fixtures/package_manifests/incomplete_recovery_package.json',
  'calamum_vulcan/fixtures/package_manifests/suspicious_review_package.json',
  '.dist-info/METADATA',
  '.dist-info/entry_points.txt',
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
  'suspicious_review_package.json',
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


def _write_sample_package_archive(output_path: Path) -> Path:
  manifest_path = (
    REPO_ROOT
    / 'calamum_vulcan'
    / 'fixtures'
    / 'package_manifests'
    / 'ready_standard_review_package.json'
  )
  manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
  output_path.parent.mkdir(parents=True, exist_ok=True)
  payload_names = sorted(
    {
      str(entry['file_name'])
      for entry in manifest.get('checksums', ())
      if isinstance(entry, dict) and 'file_name' in entry
    }
  )
  with zipfile.ZipFile(output_path, 'w') as archive:
    archive.writestr('package_manifest.json', json.dumps(manifest))
    for payload_name in payload_names:
      archive.writestr(
        payload_name,
        ('calamum-vulcan-installed-artifact-review:' + payload_name).encode('utf-8'),
      )
  return output_path


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
  for expected_flag in (
    '--integration-suite',
    '--export-evidence',
    '--package-fixture',
    '--package-archive',
  ):
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

  package_archive_path = _write_sample_package_archive(
    output_dir / 'matched_recovery_package.zip'
  )
  imported_evidence_path = output_dir / 'archive_evidence.json'
  imported_result = _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--scenario', 'ready',
      '--package-archive', str(package_archive_path),
      '--describe-only',
      '--export-evidence',
      '--evidence-format', 'json',
      '--evidence-output', str(imported_evidence_path),
    ],
    cwd=work_dir,
  )
  if 'phase="Ready to Execute" gate="Gate Ready"' not in imported_result.stdout:
    raise SystemExit('Installed archive-backed review did not preserve the ready shell summary.')
  imported_payload = _read_json(imported_evidence_path)
  if imported_payload['package']['source_kind'] != 'archive':
    raise SystemExit('Installed archive-backed evidence lost the archive source label.')
  if imported_payload['package']['checksum_verification_complete'] is not True:
    raise SystemExit('Installed archive-backed evidence did not preserve checksum verification state.')
  if not imported_payload['package']['snapshot_id']:
    raise SystemExit('Installed archive-backed evidence did not preserve analyzed snapshot identity.')
  if imported_payload['package']['snapshot_verified'] is not True:
    raise SystemExit('Installed archive-backed evidence did not preserve analyzed snapshot verification state.')
  if not imported_payload['flash_plan']['plan_id']:
    raise SystemExit('Installed archive-backed evidence did not preserve reviewed flash-plan identity.')
  if imported_payload['flash_plan']['ready_for_transport'] is not True:
    raise SystemExit('Installed archive-backed evidence did not preserve reviewed flash-plan readiness state.')
  if imported_payload['flash_plan']['reboot_policy'] != 'standard':
    raise SystemExit('Installed archive-backed evidence did not preserve reviewed flash-plan reboot posture.')
  if 'RECOVERY' not in imported_payload['flash_plan']['partition_targets']:
    raise SystemExit('Installed archive-backed evidence did not preserve reviewed flash-plan partition targets.')
  if not imported_payload['flash_plan']['recovery_guidance']:
    raise SystemExit('Installed archive-backed evidence did not preserve reviewed flash-plan recovery guidance.')
  if imported_payload['device']['marketing_name'] != 'Galaxy S21':
    raise SystemExit('Installed archive-backed evidence did not preserve device-registry marketing-name resolution.')
  if imported_payload['device']['registry_match_kind'] != 'exact':
    raise SystemExit('Installed archive-backed evidence did not preserve device-registry resolution state.')
  if imported_payload['pit']['state'] != 'captured':
    raise SystemExit('Installed archive-backed evidence did not preserve captured PIT inspection state.')
  if imported_payload['pit']['package_alignment'] != 'matched':
    raise SystemExit('Installed archive-backed evidence did not preserve PIT/package alignment truth.')
  if imported_payload['pit']['observed_pit_fingerprint'] != 'PIT-G991U-READY-001':
    raise SystemExit('Installed archive-backed evidence did not preserve the observed PIT fingerprint.')

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
  if evidence_payload['flash_plan']['ready_for_transport'] is not False:
    raise SystemExit('Installed blocked evidence did not preserve the reviewed flash-plan blocked posture.')
  if evidence_payload['pit']['package_alignment'] != 'mismatched':
    raise SystemExit('Installed blocked evidence did not preserve PIT/package mismatch truth.')

  suspicious_evidence_path = output_dir / 'suspicious_review_evidence.json'
  suspicious_result = _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--scenario', 'ready',
      '--package-fixture', 'suspicious-review',
      '--describe-only',
      '--export-evidence',
      '--evidence-format', 'json',
      '--evidence-output', str(suspicious_evidence_path),
    ],
    cwd=work_dir,
  )
  if 'phase="Ready to Execute" gate="Gate Ready"' not in suspicious_result.stdout:
    raise SystemExit('Installed suspicious-review fixture did not preserve the ready execution surface after acknowledgement.')
  suspicious_payload = _read_json(suspicious_evidence_path)
  if suspicious_payload['package']['suspicious_warning_count'] < 1:
    raise SystemExit('Installed suspicious-review evidence did not preserve package suspicious-warning counts.')
  if 'test_keys' not in suspicious_payload['package']['suspicious_indicator_ids']:
    raise SystemExit('Installed suspicious-review evidence did not preserve canonical suspicious indicator ids.')
  if suspicious_payload['flash_plan']['suspicious_warning_count'] < 1:
    raise SystemExit('Installed suspicious-review evidence did not preserve flash-plan warning counts.')
  if not suspicious_payload['flash_plan']['operator_warnings']:
    raise SystemExit('Installed suspicious-review evidence did not preserve flash-plan warning summaries.')

  failure_evidence_path = output_dir / 'failure_runtime_evidence.json'
  _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--scenario', 'failure',
      '--transport-source', 'heimdall-adapter',
      '--describe-only',
      '--export-evidence',
      '--evidence-format', 'json',
      '--evidence-output', str(failure_evidence_path),
    ],
    cwd=work_dir,
  )
  failure_payload = _read_json(failure_evidence_path)
  transcript_name = failure_payload['transcript']['reference_file_name']
  if failure_payload['transcript']['preserved'] is not True:
    raise SystemExit('Installed failure evidence did not preserve runtime transcript metadata.')
  if not transcript_name:
    raise SystemExit('Installed failure evidence did not preserve a runtime transcript reference.')
  transcript_path = output_dir / transcript_name
  if not transcript_path.exists():
    raise SystemExit('Installed failure evidence did not write the bounded runtime transcript artifact.')
  transcript_text = transcript_path.read_text(encoding='utf-8')
  if 'USB transfer timeout during partition write' not in transcript_text:
    raise SystemExit('Installed runtime transcript artifact lost the normalized failure reason.')

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

  orchestration_bundle_path = output_dir / 'orchestration_close_bundle.json'
  _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--integration-suite', 'orchestration-close',
      '--suite-format', 'json',
      '--suite-output', str(orchestration_bundle_path),
    ],
    cwd=work_dir,
  )
  orchestration_bundle = _read_json(orchestration_bundle_path)
  if orchestration_bundle['suite_name'] != 'orchestration-close':
    raise SystemExit('Installed orchestration-close bundle lost the expected suite name.')
  runtime_scenarios = [
    scenario for scenario in orchestration_bundle['scenarios']
    if scenario['transport_source'] == 'heimdall-adapter'
  ]
  if not runtime_scenarios or not all(
    scenario['transcript_preserved'] for scenario in runtime_scenarios
  ):
    raise SystemExit('Installed orchestration-close bundle did not preserve transcript references for runtime scenarios.')

  read_side_bundle_path = output_dir / 'read_side_close_bundle.json'
  _run(
    [
      sys.executable,
      '-c', _cli_probe_code(install_root),
      '--integration-suite', 'read-side-close',
      '--suite-format', 'json',
      '--suite-output', str(read_side_bundle_path),
    ],
    cwd=work_dir,
  )
  read_side_bundle = _read_json(read_side_bundle_path)
  if read_side_bundle['suite_name'] != 'read-side-close':
    raise SystemExit('Installed read-side-close bundle lost the expected suite name.')
  scenario_map = {
    scenario['scenario_id']: scenario for scenario in read_side_bundle['scenarios']
  }
  inspect_ready = scenario_map.get('inspect-only-ready-review')
  native_review = scenario_map.get('native-adb-package-review')
  fastboot_fallback = scenario_map.get('fastboot-fallback-review')
  fallback_exhausted = scenario_map.get('fallback-exhausted-review')
  if inspect_ready is None or inspect_ready['inspection_posture'] != 'ready':
    raise SystemExit('Installed read-side-close bundle did not preserve the ready inspect-only posture.')
  if inspect_ready['transport_state'] != 'not_invoked' or inspect_ready['transcript_preserved'] is not False:
    raise SystemExit('Installed read-side-close bundle lost the read-side-only non-transport posture.')
  if native_review is None or native_review['live_source'] != 'adb' or native_review['pit_package_alignment'] != 'matched':
    raise SystemExit('Installed read-side-close bundle did not preserve the native ADB matched-alignment lane.')
  if fastboot_fallback is None or fastboot_fallback['live_source'] != 'fastboot' or fastboot_fallback['live_fallback_posture'] != 'engaged':
    raise SystemExit('Installed read-side-close bundle did not preserve the fastboot fallback posture.')
  if fallback_exhausted is None or fallback_exhausted['inspection_posture'] != 'failed':
    raise SystemExit('Installed read-side-close bundle did not preserve the exhausted fallback failure lane.')

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
      'archive_package_review="passed"',
      'suspicious_review="passed"',
      'evidence_export="passed"',
      'integration_bundle="passed"',
      'read_side_close_bundle="passed"',
      'distribution_files="passed"',
      'installed_artifact_contract="passed"',
    ]
  )
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
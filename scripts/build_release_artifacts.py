"""Build and inspect Calamum Vulcan release artifacts from the repo root."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import zipfile
from importlib.util import find_spec
from pathlib import Path
from typing import Iterable
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.validation import run_security_validation_suite
from calamum_vulcan.validation import write_security_validation_artifacts


DIST_DIR = REPO_ROOT / 'dist'
ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'fs_p02_build_artifacts'
EXPECTED_WHEEL_SUFFIXES = (
  'calamum_vulcan/__init__.py',
  'calamum_vulcan/app/__main__.py',
  'calamum_vulcan/launch_shell.py',
  'calamum_vulcan/assets/branding/calamum_logo_color.png',
  'calamum_vulcan/assets/branding/calamum_taskbar_icon.png',
  'calamum_vulcan/fixtures/package_manifests/matched_recovery_package.json',
)
EXPECTED_SDIST_SUFFIXES = (
  'pyproject.toml',
  'README.md',
  'CHANGELOG.md',
  'CONTRIBUTING.md',
  'LICENSE',
  'calamum_vulcan/assets/branding/calamum_logo_color.png',
  'calamum_vulcan/assets/branding/calamum_taskbar_icon.png',
  'calamum_vulcan/fixtures/package_manifests/matched_recovery_package.json',
  'tests/unit/test_integration_suite.py',
)
FORBIDDEN_SDIST_PREFIXES = (
  'docs/',
  'temp/',
)


def _print(lines: Sequence[str]) -> None:
  for line in lines:
    print(line)


def _require_build_module() -> None:
  if find_spec('build') is None:
    raise SystemExit(
      'Missing build module. Install release tooling first with '
      '`python -m pip install -e .[release]`.'
    )


def _run(command: Sequence[str]) -> None:
  result = subprocess.run(
    command,
    cwd=REPO_ROOT,
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    if result.stdout:
      print(result.stdout)
    if result.stderr:
      print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode)


def _contains_suffix(names: Iterable[str], expected_suffix: str) -> bool:
  return any(name.endswith(expected_suffix) for name in names)


def _inspect_wheel(wheel_path: Path) -> None:
  with zipfile.ZipFile(wheel_path) as wheel_file:
    names = wheel_file.namelist()
  missing = [
    suffix for suffix in EXPECTED_WHEEL_SUFFIXES if not _contains_suffix(names, suffix)
  ]
  if missing:
    raise SystemExit(
      'Wheel is missing expected entries: {missing}'.format(
        missing=', '.join(missing)
      )
    )


def _inspect_sdist(sdist_path: Path) -> None:
  with tarfile.open(sdist_path, 'r:gz') as sdist_file:
    names = sdist_file.getnames()
  missing = [
    suffix for suffix in EXPECTED_SDIST_SUFFIXES if not _contains_suffix(names, suffix)
  ]
  if missing:
    raise SystemExit(
      'sdist is missing expected entries: {missing}'.format(
        missing=', '.join(missing)
      )
    )
  leaked = []
  for name in names:
    relative_name = name.split('/', 1)[1] if '/' in name else name
    if any(relative_name.startswith(prefix) for prefix in FORBIDDEN_SDIST_PREFIXES):
      leaked.append(relative_name)
  if leaked:
    raise SystemExit(
      'sdist leaked forbidden entries: {leaked}'.format(
        leaked=', '.join(sorted(set(leaked)))
      )
    )


def main() -> int:
  _require_build_module()

  if DIST_DIR.exists():
    shutil.rmtree(DIST_DIR)

  for egg_info_dir in REPO_ROOT.glob('*.egg-info'):
    if egg_info_dir.is_dir():
      shutil.rmtree(egg_info_dir)

  _run([sys.executable, '-m', 'build', '--sdist', '--wheel'])

  wheels = sorted(DIST_DIR.glob('*.whl'))
  sdists = sorted(DIST_DIR.glob('*.tar.gz'))
  if len(wheels) != 1 or len(sdists) != 1:
    raise SystemExit(
      'Expected exactly one wheel and one sdist, found {wheel_count} wheel(s) and '
      '{sdist_count} sdist(s).'.format(
        wheel_count=len(wheels),
        sdist_count=len(sdists),
      )
    )

  wheel_path = wheels[0]
  sdist_path = sdists[0]
  _inspect_wheel(wheel_path)
  _inspect_sdist(sdist_path)
  security_summary = run_security_validation_suite(REPO_ROOT)
  write_security_validation_artifacts(ARCHIVE_ROOT / 'security_validation', security_summary)
  if security_summary.decision == 'failed':
    raise SystemExit('Security validation failed for the FS-P02 build closure.')

  _print(
    [
      'build_root="{root}"'.format(root=REPO_ROOT),
      'sdist="{sdist}"'.format(sdist=sdist_path.name),
      'wheel="{wheel}"'.format(wheel=wheel_path.name),
      'security_validation="{decision}"'.format(
        decision=security_summary.decision,
      ),
      'artifact_contract="passed"',
    ]
  )
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
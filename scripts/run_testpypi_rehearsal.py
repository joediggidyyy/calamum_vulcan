"""Run the FS-P06 TestPyPI rehearsal and publication gate."""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import venv
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
  sys.path.insert(0, str(REPO_ROOT))

from calamum_vulcan.validation import run_security_validation_suite
from calamum_vulcan.validation import write_security_validation_artifacts


DIST_DIR = REPO_ROOT / 'dist'
ARCHIVE_ROOT = REPO_ROOT / 'temp' / 'fs_p06_testpypi_rehearsal'
VALIDATION_ROOT = Path(tempfile.gettempdir()) / 'calamum_vulcan_fs_p06_testpypi_rehearsal'
PYPROJECT_PATH = REPO_ROOT / 'pyproject.toml'
TESTPYPI_REPOSITORY_URL = 'https://test.pypi.org/legacy/'
TESTPYPI_SIMPLE_URL = 'https://test.pypi.org/simple/'
PYPI_SIMPLE_URL = 'https://pypi.org/simple/'
REGISTRY_INSTALL_RETRY_ATTEMPTS = 12
REGISTRY_INSTALL_RETRY_DELAY_SECONDS = 10
REGISTRY_INSTALL_RETRY_MARKERS = (
  'Could not find a version that satisfies the requirement',
  'No matching distribution found for',
)


def _print(lines: Sequence[str]) -> None:
  for line in lines:
    print(line)


def _write_text(path: Path, content: str) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding='utf-8')


def _append_log(path: Path, line: str) -> None:
  with path.open('a', encoding='utf-8') as handle:
    handle.write(line + '\n')


def _run(
  command: Sequence[str],
  cwd: Path,
  env: Optional[Mapping[str, str]] = None,
  allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
  result = subprocess.run(
    command,
    cwd=cwd,
    capture_output=True,
    text=True,
    env=dict(env) if env is not None else None,
  )
  if result.returncode != 0 and not allow_failure:
    if result.stdout:
      print(result.stdout)
    if result.stderr:
      print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode)
  return result


def _is_registry_install_retryable(result: subprocess.CompletedProcess[str]) -> bool:
  """Return whether a failed registry install likely needs propagation retries."""

  if result.returncode == 0:
    return False
  combined_output = '\n'.join(
    part for part in (result.stdout, result.stderr) if part
  )
  return any(marker in combined_output for marker in REGISTRY_INSTALL_RETRY_MARKERS)


def _run_registry_install_command(
  command: Sequence[str],
  cwd: Path,
  env: Mapping[str, str],
  progress_path: Path,
) -> subprocess.CompletedProcess[str]:
  """Install from TestPyPI with bounded retries for index propagation lag."""

  last_result = None  # type: Optional[subprocess.CompletedProcess[str]]
  for attempt in range(1, REGISTRY_INSTALL_RETRY_ATTEMPTS + 1):
    result = _run(command, cwd=cwd, env=env, allow_failure=True)
    if result.returncode == 0:
      return result
    last_result = result
    if not _is_registry_install_retryable(result):
      break
    if attempt == REGISTRY_INSTALL_RETRY_ATTEMPTS:
      break
    _append_log(
      progress_path,
      '[registry] package not visible yet; retry {attempt}/{total} after {delay}s'.format(
        attempt=attempt,
        total=REGISTRY_INSTALL_RETRY_ATTEMPTS,
        delay=REGISTRY_INSTALL_RETRY_DELAY_SECONDS,
      ),
    )
    time.sleep(REGISTRY_INSTALL_RETRY_DELAY_SECONDS)

  assert last_result is not None
  if last_result.stdout:
    print(last_result.stdout)
  if last_result.stderr:
    print(last_result.stderr, file=sys.stderr)
  raise SystemExit(last_result.returncode)


def _load_dotenv(path: Path) -> None:
  if not path.exists():
    return
  for raw_line in path.read_text(encoding='utf-8').splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#') or '=' not in line:
      continue
    key, value = line.split('=', 1)
    key = key.strip()
    value = value.strip()
    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
      value = value[1:-1]
    os.environ.setdefault(key, value)


def _find_single_file(pattern: str) -> Path:
  matches = sorted(DIST_DIR.glob(pattern))
  if len(matches) != 1:
    raise SystemExit(
      'Expected exactly one artifact matching {pattern}, found {count}. Run '
      '`python scripts/build_release_artifacts.py` first.'.format(
        pattern=pattern,
        count=len(matches),
      )
    )
  return matches[0]


def _artifact_hash(path: Path) -> Dict[str, object]:
  digest = hashlib.sha256()
  with path.open('rb') as handle:
    for chunk in iter(lambda: handle.read(65536), b''):
      digest.update(chunk)
  return {
    'name': path.name,
    'size_bytes': path.stat().st_size,
    'sha256': digest.hexdigest(),
  }


def _project_metadata() -> Dict[str, object]:
  with PYPROJECT_PATH.open('rb') as handle:
    pyproject = tomllib.load(handle)
  project = pyproject['project']
  wheel_path = _find_single_file('*.whl')
  wheel_stem_parts = wheel_path.stem.split('-')
  wheel_tags = '-'.join(wheel_stem_parts[2:])
  return {
    'name': project['name'],
    'normalized_name': project['name'].replace('_', '-'),
    'version': project['version'],
    'requires_python': project['requires-python'],
    'dependencies': list(project.get('dependencies', [])),
    'urls': dict(project.get('urls', {})),
    'wheel_tags': wheel_tags,
  }


def _twine_env() -> Dict[str, str]:
  env = dict(os.environ)
  token = None
  for candidate in (
    env.get('CALAMUM_VULCAN_TESTPYPI_TOKEN'),
    env.get('TWINE_PASSWORD'),
  ):
    if _is_configured_secret(candidate):
      token = candidate
      break
  username = env.get('TWINE_USERNAME', '__token__')
  if token:
    env['TWINE_USERNAME'] = username
    env['TWINE_PASSWORD'] = token
  env.setdefault('TWINE_NON_INTERACTIVE', '1')
  return env


def _is_configured_secret(value: Optional[str]) -> bool:
  if not value:
    return False
  normalized = value.strip()
  if not normalized:
    return False
  placeholder_markers = (
    'YOUR_TESTPYPI_TOKEN_HERE',
    'YOUR_PYPI_TOKEN_HERE',
    'YOUR_TOKEN_HERE',
  )
  return not any(marker in normalized for marker in placeholder_markers)


def _pypirc_summary() -> Dict[str, object]:
  path = Path.home() / '.pypirc'
  if not path.exists():
    return {
      'path': str(path),
      'present': False,
      'sections': [],
      'testpypi_configured': False,
    }
  parser = configparser.RawConfigParser()
  parser.read(path, encoding='utf-8')
  sections = parser.sections()
  return {
    'path': str(path),
    'present': True,
    'sections': sections,
    'testpypi_configured': parser.has_section('testpypi'),
  }


def _credential_summary(pypirc: Mapping[str, object]) -> Dict[str, object]:
  token_present = _is_configured_secret(os.environ.get('CALAMUM_VULCAN_TESTPYPI_TOKEN'))
  twine_password_present = _is_configured_secret(os.environ.get('TWINE_PASSWORD'))
  return {
    'dotenv_loaded': (REPO_ROOT / '.env').exists(),
    'token_env_present': token_present,
    'twine_password_present': twine_password_present,
    'twine_username': os.environ.get('TWINE_USERNAME', '__token__'),
    'pypirc_present': bool(pypirc['present']),
    'pypirc_sections': list(pypirc['sections']),
    'pypirc_testpypi_configured': bool(pypirc['testpypi_configured']),
    'ready_for_upload': token_present or (
      twine_password_present and os.environ.get('TWINE_USERNAME') == '__token__'
    ) or bool(pypirc['testpypi_configured']),
  }


def _twine_upload_command(
  wheel_path: Path,
  sdist_path: Path,
  credentials: Mapping[str, object],
) -> Sequence[str]:
  command = [
    sys.executable,
    '-m', 'twine', 'upload',
    '--non-interactive',
    '--skip-existing',
  ]
  if credentials['token_env_present'] or credentials['twine_password_present']:
    command.extend(['--repository-url', TESTPYPI_REPOSITORY_URL])
  else:
    command.extend(['--repository', 'testpypi'])
  command.extend([str(wheel_path), str(sdist_path)])
  return command


def _venv_python(venv_root: Path) -> Path:
  if sys.platform.startswith('win'):
    return venv_root / 'Scripts' / 'python.exe'
  return venv_root / 'bin' / 'python'


def _venv_entrypoint(venv_root: Path, command_name: str) -> Path:
  if sys.platform.startswith('win'):
    return venv_root / 'Scripts' / (command_name + '.exe')
  return venv_root / 'bin' / command_name


def _create_clean_venv(venv_root: Path) -> Path:
  if venv_root.exists():
    shutil.rmtree(venv_root)
  builder = venv.EnvBuilder(with_pip=True, clear=True)
  builder.create(venv_root)
  python_path = _venv_python(venv_root)
  if not python_path.exists():
    raise SystemExit('Failed to create validation venv at {root}.'.format(root=venv_root))
  return python_path


def _metadata_probe_code() -> str:
  return """
from importlib import metadata
import json

dist = metadata.distribution('calamum_vulcan')
payload = {
  'name': dist.metadata['Name'],
  'version': dist.version,
  'summary': dist.metadata['Summary'],
  'requires_python': dist.metadata['Requires-Python'],
  'license': dist.metadata.get('License'),
  'classifiers': dist.metadata.get_all('Classifier') or [],
  'requires_dist': dist.metadata.get_all('Requires-Dist') or [],
  'project_urls': dist.metadata.get_all('Project-URL') or [],
}
print(json.dumps(payload, indent=2, sort_keys=True))
"""


def _run_registry_install_validation(
  project: Mapping[str, object],
  validation_root: Path,
  progress_path: Path,
) -> Dict[str, object]:
  venv_root = validation_root / 'registry_install_env'
  python_path = _create_clean_venv(venv_root)
  command_name = 'calamum-vulcan'
  gui_command_name = 'calamum-vulcan-gui'
  install_env = dict(os.environ)
  install_env.pop('QT_QPA_PLATFORM', None)
  install_env.setdefault('PIP_DISABLE_PIP_VERSION_CHECK', '1')
  install_env.setdefault('PIP_PROGRESS_BAR', 'off')
  install_env.setdefault('PYTHONUTF8', '1')
  captured_at = '2026-04-18T23:58:00Z'
  install_command = [
    str(python_path),
    '-m', 'pip', 'install',
    '--index-url', TESTPYPI_SIMPLE_URL,
    '--extra-index-url', PYPI_SIMPLE_URL,
    '--no-cache-dir',
    '{name}=={version}'.format(
      name=project['name'],
      version=project['version'],
    ),
  ]
  _append_log(progress_path, '[registry] create clean environment')
  _run([str(python_path), '-m', 'pip', '--version'], cwd=validation_root, env=install_env)
  _append_log(progress_path, '[registry] install from TestPyPI + PyPI dependency index')
  install_result = _run_registry_install_command(
    install_command,
    cwd=validation_root,
    env=install_env,
    progress_path=progress_path,
  )
  _write_text(validation_root / 'registry_install_stdout.txt', install_result.stdout)
  _write_text(validation_root / 'registry_install_stderr.txt', install_result.stderr)

  help_result = _run(
    [str(_venv_entrypoint(venv_root, command_name)), '--help'],
    cwd=validation_root,
    env=install_env,
  )
  if '--integration-suite' not in help_result.stdout:
    raise SystemExit('Registry-installed help output is missing --integration-suite.')
  _write_text(validation_root / 'registry_help.txt', help_result.stdout)

  describe_result = _run(
    [
      str(_venv_entrypoint(venv_root, command_name)),
      '--scenario', 'ready',
      '--describe-only',
      '--captured-at-utc', captured_at,
    ],
    cwd=validation_root,
    env=install_env,
  )
  if 'phase="Ready to Execute" gate="Gate Ready"' not in describe_result.stdout:
    raise SystemExit('Registry-installed ready scenario did not preserve the expected shell summary.')
  _write_text(validation_root / 'registry_ready.txt', describe_result.stdout)

  bundle_path = validation_root / 'registry_sprint_close_bundle.md'
  _run(
    [
      str(_venv_entrypoint(venv_root, command_name)),
      '--integration-suite', 'sprint-close',
      '--suite-format', 'markdown',
      '--suite-output', str(bundle_path),
      '--captured-at-utc', captured_at,
    ],
    cwd=validation_root,
    env=install_env,
  )
  bundle_markdown = bundle_path.read_text(encoding='utf-8')
  if 'Calamum Vulcan FS-08 sprint-close bundle' not in bundle_markdown:
    raise SystemExit('Registry-installed sprint-close bundle is missing the expected heading.')

  safe_path_bundle_path = validation_root / 'registry_safe_path_close_bundle.md'
  _run(
    [
      str(_venv_entrypoint(venv_root, command_name)),
      '--integration-suite', 'safe-path-close',
      '--suite-format', 'markdown',
      '--suite-output', str(safe_path_bundle_path),
      '--captured-at-utc', captured_at,
    ],
    cwd=validation_root,
    env=install_env,
  )
  safe_path_bundle_markdown = safe_path_bundle_path.read_text(encoding='utf-8')
  if 'Calamum Vulcan FS4-07 safe-path-close bundle' not in safe_path_bundle_markdown:
    raise SystemExit('Registry-installed safe-path-close bundle is missing the expected heading.')

  metadata_result = _run(
    [str(python_path), '-c', _metadata_probe_code()],
    cwd=validation_root,
    env=install_env,
  )
  metadata_payload = json.loads(metadata_result.stdout)
  _write_text(validation_root / 'registry_metadata.json', metadata_result.stdout)

  uninstall_result = _run(
    [str(python_path), '-m', 'pip', 'uninstall', '-y', project['name']],
    cwd=validation_root,
    env=install_env,
  )
  _write_text(validation_root / 'registry_uninstall.txt', uninstall_result.stdout + uninstall_result.stderr)
  probe_missing = _run(
    [str(python_path), '-m', 'pip', 'show', project['name']],
    cwd=validation_root,
    env=install_env,
    allow_failure=True,
  )
  if probe_missing.returncode == 0:
    raise SystemExit('Registry uninstall did not remove the installed distribution cleanly.')

  reinstall_result = _run(install_command, cwd=validation_root, env=install_env)
  _write_text(validation_root / 'registry_reinstall_stdout.txt', reinstall_result.stdout)
  _write_text(validation_root / 'registry_reinstall_stderr.txt', reinstall_result.stderr)

  gui_entrypoint_path = _venv_entrypoint(venv_root, gui_command_name)
  gui_entrypoint_exists = gui_entrypoint_path.exists()

  return {
    'validation_root': str(validation_root),
    'install': 'passed',
    'help': 'passed',
    'describe': 'passed',
    'bundle': 'passed',
    'metadata': metadata_payload,
    'uninstall_reinstall': 'passed',
    'gui_entrypoint_present': gui_entrypoint_exists,
  }


def _markdown_summary(
  summary: Mapping[str, object],
  blockers: Iterable[str],
) -> str:
  lines = [
    '## FS-P06 TestPyPI rehearsal summary',
    '',
    '- decision: `{decision}`'.format(decision=summary['publication_decision']),
    '- version: `{version}`'.format(version=summary['project']['version']),
    '- wheel tags: `{tags}`'.format(tags=summary['project']['wheel_tags']),
    '- twine check: `{status}`'.format(status=summary['twine_check']),
    '- upload attempted: `{status}`'.format(status=summary['upload']['attempted']),
    '- upload result: `{status}`'.format(status=summary['upload']['status']),
    '- security validation: `{status}`'.format(
      status=summary['security_validation']['decision'],
    ),
    '',
    '### Artifact hashes',
    '',
  ]
  for artifact in summary['artifacts']:
    lines.append(
      '- `{name}`: `{sha}` ({size} bytes)'.format(
        name=artifact['name'],
        sha=artifact['sha256'],
        size=artifact['size_bytes'],
      )
    )
  lines.extend(['', '### Credential surface', ''])
  lines.append(
    '- ready for upload: `{ready}`'.format(
      ready=summary['credentials']['ready_for_upload'],
    )
  )
  lines.append(
    '- env token present: `{present}`'.format(
      present=summary['credentials']['token_env_present'],
    )
  )
  lines.append(
    '- `.pypirc` testpypi configured: `{present}`'.format(
      present=summary['credentials']['pypirc_testpypi_configured'],
    )
  )
  lines.extend(['', '### Blockers', ''])
  if blockers:
    for blocker in blockers:
      lines.append('- ' + blocker)
  else:
    lines.append('- none')
  return '\n'.join(lines) + '\n'


def main() -> int:
  _load_dotenv(REPO_ROOT / '.env')
  project = _project_metadata()
  pypirc = _pypirc_summary()
  credentials = _credential_summary(pypirc)

  wheel_path = _find_single_file('*.whl')
  sdist_path = _find_single_file('*.tar.gz')

  if ARCHIVE_ROOT.exists():
    shutil.rmtree(ARCHIVE_ROOT)
  ARCHIVE_ROOT.mkdir(parents=True)

  if VALIDATION_ROOT.exists():
    shutil.rmtree(VALIDATION_ROOT)
  VALIDATION_ROOT.mkdir(parents=True)

  progress_path = ARCHIVE_ROOT / 'progress.log'
  blockers = []

  twine_env = _twine_env()
  twine_check = _run(
    [sys.executable, '-m', 'twine', 'check', str(wheel_path), str(sdist_path)],
    cwd=REPO_ROOT,
  )
  _write_text(ARCHIVE_ROOT / 'twine_check_stdout.txt', twine_check.stdout)
  _write_text(ARCHIVE_ROOT / 'twine_check_stderr.txt', twine_check.stderr)
  _append_log(progress_path, '[preflight] twine check passed')

  upload_summary = {
    'attempted': False,
    'status': 'not-run',
    'stdout_path': None,
    'stderr_path': None,
    'project_url': 'https://test.pypi.org/project/{name}/'.format(
      name=project['normalized_name'],
    ),
  }
  registry_validation = None

  if credentials['ready_for_upload']:
    upload_summary['attempted'] = True
    upload_result = _run(
      _twine_upload_command(wheel_path, sdist_path, credentials),
      cwd=REPO_ROOT,
      env=twine_env,
      allow_failure=True,
    )
    upload_stdout_path = ARCHIVE_ROOT / 'twine_upload_stdout.txt'
    upload_stderr_path = ARCHIVE_ROOT / 'twine_upload_stderr.txt'
    _write_text(upload_stdout_path, upload_result.stdout)
    _write_text(upload_stderr_path, upload_result.stderr)
    upload_summary['stdout_path'] = str(upload_stdout_path)
    upload_summary['stderr_path'] = str(upload_stderr_path)
    if upload_result.returncode == 0:
      upload_summary['status'] = 'passed'
      _append_log(progress_path, '[upload] TestPyPI upload passed or artifacts already existed')
      registry_validation = _run_registry_install_validation(
        project,
        VALIDATION_ROOT,
        progress_path,
      )
    else:
      upload_summary['status'] = 'failed'
      blockers.append('TestPyPI upload failed; inspect twine upload logs under temp/fs_p06_testpypi_rehearsal/.')
  else:
    blockers.append('No TestPyPI credential is configured via CALAMUM_VULCAN_TESTPYPI_TOKEN/TWINE_PASSWORD, and no [testpypi] profile exists in the user-level .pypirc.')

  if registry_validation is None and not blockers:
    blockers.append('Registry-delivered install validation did not run.')

  security_summary = run_security_validation_suite(REPO_ROOT)
  write_security_validation_artifacts(ARCHIVE_ROOT / 'security_validation', security_summary)
  if security_summary.decision == 'failed':
    blockers.append('Security validation failed; inspect temp/fs_p06_testpypi_rehearsal/security_validation/.')

  publication_decision = 'go' if not blockers and registry_validation is not None else 'no-go'
  summary = {
    'project': project,
    'artifacts': [
      _artifact_hash(wheel_path),
      _artifact_hash(sdist_path),
    ],
    'twine_check': 'passed',
    'credentials': credentials,
    'upload': upload_summary,
    'registry_validation': registry_validation,
    'security_validation': {
      'decision': security_summary.decision,
      'blocking_findings': len(security_summary.blocking_findings),
      'warnings': len(security_summary.warnings),
    },
    'publication_decision': publication_decision,
    'blockers': blockers,
  }
  summary_json_path = ARCHIVE_ROOT / 'testpypi_rehearsal_summary.json'
  summary_md_path = ARCHIVE_ROOT / 'testpypi_rehearsal_summary.md'
  _write_text(summary_json_path, json.dumps(summary, indent=2, sort_keys=True) + '\n')
  _write_text(summary_md_path, _markdown_summary(summary, blockers))

  if publication_decision == 'go':
    _print(
      [
        'archive_root="{root}"'.format(root=ARCHIVE_ROOT),
        'wheel="{wheel}"'.format(wheel=wheel_path.name),
        'sdist="{sdist}"'.format(sdist=sdist_path.name),
        'security_validation="{decision}"'.format(
          decision=security_summary.decision,
        ),
        'twine_check="passed"',
        'testpypi_upload="passed"',
        'registry_install="passed"',
        'uninstall_reinstall="passed"',
        'publication_decision="go"',
        'testpypi_rehearsal_contract="passed"',
      ]
    )
  else:
    _print(
      [
        'archive_root="{root}"'.format(root=ARCHIVE_ROOT),
        'wheel="{wheel}"'.format(wheel=wheel_path.name),
        'sdist="{sdist}"'.format(sdist=sdist_path.name),
        'security_validation="{decision}"'.format(
          decision=security_summary.decision,
        ),
        'twine_check="passed"',
        'testpypi_upload="{status}"'.format(status=upload_summary['status']),
        'registry_install="not-run"',
        'publication_decision="no-go"',
        'blocker_count="{count}"'.format(count=len(blockers)),
        'testpypi_rehearsal_contract="blocked"',
      ]
    )
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
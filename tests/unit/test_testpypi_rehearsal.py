"""Tests for the FS-P06 TestPyPI rehearsal runner."""

from __future__ import annotations

import sys
from pathlib import Path
import tomllib
import unittest
import subprocess
from unittest.mock import patch


FINAL_EXAM_ROOT = Path(__file__).resolve().parents[2]
if str(FINAL_EXAM_ROOT) not in sys.path:
  sys.path.insert(0, str(FINAL_EXAM_ROOT))

PROJECT_VERSION = tomllib.loads(
  (FINAL_EXAM_ROOT / 'pyproject.toml').read_text(encoding='utf-8')
)['project']['version']

from scripts.run_testpypi_rehearsal import _is_registry_install_retryable
from scripts.run_testpypi_rehearsal import _run_registry_install_command
from scripts.run_testpypi_rehearsal import _twine_upload_command


class TestPyPIRehearsalTests(unittest.TestCase):
  """Verify the rehearsal runner chooses the correct Twine credential path."""

  def _artifact_paths(self) -> tuple[Path, Path]:
    wheel_path = Path(
      'dist/calamum_vulcan-{version}-py3-none-any.whl'.format(
        version=PROJECT_VERSION,
      )
    )
    sdist_path = Path(
      'dist/calamum_vulcan-{version}.tar.gz'.format(version=PROJECT_VERSION)
    )
    return wheel_path, sdist_path

  def test_upload_command_uses_repository_profile_for_pypirc_credentials(self) -> None:
    wheel_path, sdist_path = self._artifact_paths()
    credentials = {
      'token_env_present': False,
      'twine_password_present': False,
      'pypirc_testpypi_configured': True,
    }

    command = list(_twine_upload_command(wheel_path, sdist_path, credentials))

    self.assertIn('--repository', command)
    self.assertIn('testpypi', command)
    self.assertNotIn('--repository-url', command)

  def test_upload_command_uses_repository_url_for_env_credentials(self) -> None:
    wheel_path, sdist_path = self._artifact_paths()
    credentials = {
      'token_env_present': True,
      'twine_password_present': False,
      'pypirc_testpypi_configured': False,
    }

    command = list(_twine_upload_command(wheel_path, sdist_path, credentials))

    self.assertIn('--repository-url', command)
    self.assertNotIn('--repository', command)

  def test_registry_install_retryable_for_testpypi_propagation_lag(self) -> None:
    result = subprocess.CompletedProcess(
      args=['python', '-m', 'pip', 'install'],
      returncode=1,
      stdout='',
      stderr='ERROR: No matching distribution found for calamum_vulcan==0.2.0',
    )

    self.assertTrue(_is_registry_install_retryable(result))

  def test_registry_install_not_retryable_for_other_failures(self) -> None:
    result = subprocess.CompletedProcess(
      args=['python', '-m', 'pip', 'install'],
      returncode=1,
      stdout='',
      stderr='ERROR: Access denied',
    )

    self.assertFalse(_is_registry_install_retryable(result))

  def test_registry_install_retries_until_package_appears(self) -> None:
    retryable_failure = subprocess.CompletedProcess(
      args=['python', '-m', 'pip', 'install'],
      returncode=1,
      stdout='',
      stderr='ERROR: No matching distribution found for calamum_vulcan==0.2.0',
    )
    success = subprocess.CompletedProcess(
      args=['python', '-m', 'pip', 'install'],
      returncode=0,
      stdout='installed',
      stderr='',
    )
    appended_lines = []

    with patch(
      'scripts.run_testpypi_rehearsal._run',
      side_effect=[retryable_failure, success],
    ) as run_mock:
      with patch(
        'scripts.run_testpypi_rehearsal._append_log',
        side_effect=lambda _path, line: appended_lines.append(line),
      ):
        with patch('scripts.run_testpypi_rehearsal.time.sleep') as sleep_mock:
          result = _run_registry_install_command(
            ['python', '-m', 'pip', 'install'],
            cwd=FINAL_EXAM_ROOT,
            env={'PIP_DISABLE_PIP_VERSION_CHECK': '1'},
            progress_path=FINAL_EXAM_ROOT / 'progress.log',
          )

    self.assertEqual(result, success)
    self.assertEqual(run_mock.call_count, 2)
    self.assertEqual(sleep_mock.call_count, 1)
    self.assertEqual(len(appended_lines), 1)
    self.assertIn('package not visible yet; retry 1/', appended_lines[0])


if __name__ == '__main__':
  unittest.main()
